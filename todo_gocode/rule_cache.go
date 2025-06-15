package main

import (
	"container/list"
	"fmt"
	"sync"
	"sync/atomic"
	"time"
)

// RuleCache implements an LRU cache with TTL for rulesets
type RuleCache struct {
	cache      map[string]*list.Element
	lruList    *list.List
	maxSize    int
	defaultTTL time.Duration
	mutex      sync.RWMutex
	
	// Metrics
	hits        int64
	misses      int64
	evictions   int64
	expired     int64
	totalSets   int64
	
	// Background cleanup
	cleanupTicker *time.Ticker
	stopCleanup   chan struct{}
}

// CacheEntry represents a cached ruleset with metadata
type CacheEntry struct {
	Key       string    `json:"key"`
	RuleSet   *RuleSet  `json:"ruleset"`
	ExpiresAt time.Time `json:"expires_at"`
	CreatedAt time.Time `json:"created_at"`
	LastHit   time.Time `json:"last_hit"`
	HitCount  int64     `json:"hit_count"`
	Size      int       `json:"size_bytes"`
}

// CacheStats provides cache performance metrics
type CacheStats struct {
	Size          int     `json:"size"`
	MaxSize       int     `json:"max_size"`
	Hits          int64   `json:"hits"`
	Misses        int64   `json:"misses"`
	HitRate       float64 `json:"hit_rate"`
	Evictions     int64   `json:"evictions"`
	Expired       int64   `json:"expired"`
	TotalSets     int64   `json:"total_sets"`
	MemoryUsage   int64   `json:"memory_usage_bytes"`
	AverageHits   float64 `json:"average_hits_per_entry"`
	OldestEntry   time.Time `json:"oldest_entry,omitempty"`
	NewestEntry   time.Time `json:"newest_entry,omitempty"`
	DefaultTTL    string    `json:"default_ttl"`
}

// RuleSet structure (from previous implementations)
type RuleSet struct {
	ID               string                     `json:"ruleset_id"`
	Rules            []Rule                     `json:"rules"`
	ExternalServices map[string]ServiceConfig   `json:"external_services,omitempty"`
	Version          string                     `json:"version,omitempty"`
	CreatedAt        time.Time                  `json:"created_at,omitempty"`
}

type Rule struct {
	ID        string    `json:"id,omitempty"`
	Priority  int       `json:"priority"`
	Condition Condition `json:"condition"`
	Actions   []Action  `json:"actions"`
}

type Condition struct {
	Field    string      `json:"field"`
	Operator string      `json:"operator"`
	Value    interface{} `json:"value"`
	Type     string      `json:"type,omitempty"`
}

type Action struct {
	ID       string                 `json:"id,omitempty"`
	Type     string                 `json:"type"`
	Priority int                    `json:"priority,omitempty"`
	Target   string                 `json:"target,omitempty"`
	Params   map[string]interface{} `json:"params,omitempty"`
}

type ServiceConfig struct {
	URL     string            `json:"url"`
	Headers map[string]string `json:"headers,omitempty"`
	Auth    AuthConfig        `json:"auth,omitempty"`
}

type AuthConfig struct {
	Type   string `json:"type"`
	Token  string `json:"token,omitempty"`
	Header string `json:"header,omitempty"`
}

// NewRuleCache creates a new cache instance with specified parameters
func NewRuleCache(maxSize int, defaultTTL time.Duration) *RuleCache {
	if maxSize <= 0 {
		maxSize = 100 // Default size
	}
	
	if defaultTTL <= 0 {
		defaultTTL = 30 * time.Minute // Default TTL
	}
	
	rc := &RuleCache{
		cache:      make(map[string]*list.Element),
		lruList:    list.New(),
		maxSize:    maxSize,
		defaultTTL: defaultTTL,
		stopCleanup: make(chan struct{}),
	}
	
	// Start background cleanup goroutine
	rc.startCleanup()
	
	return rc
}

// Get retrieves a ruleset from the cache
func (rc *RuleCache) Get(id string) (*RuleSet, bool) {
	rc.mutex.Lock()
	defer rc.mutex.Unlock()
	
	element, exists := rc.cache[id]
	if !exists {
		atomic.AddInt64(&rc.misses, 1)
		return nil, false
	}
	
	entry := element.Value.(*CacheEntry)
	
	// Check if entry has expired
	if time.Now().After(entry.ExpiresAt) {
		rc.removeElement(element)
		atomic.AddInt64(&rc.misses, 1)
		atomic.AddInt64(&rc.expired, 1)
		return nil, false
	}
	
	// Move to front (most recently used)
	rc.lruList.MoveToFront(element)
	
	// Update hit statistics
	entry.LastHit = time.Now()
	atomic.AddInt64(&entry.HitCount, 1)
	atomic.AddInt64(&rc.hits, 1)
	
	return entry.RuleSet, true
}

// Set stores a ruleset in the cache with specified TTL
func (rc *RuleCache) Set(id string, ruleset *RuleSet, ttl time.Duration) {
	if ttl <= 0 {
		ttl = rc.defaultTTL
	}
	
	rc.mutex.Lock()
	defer rc.mutex.Unlock()
	
	now := time.Now()
	
	// Check if entry already exists
	if element, exists := rc.cache[id]; exists {
		// Update existing entry
		entry := element.Value.(*CacheEntry)
		entry.RuleSet = ruleset
		entry.ExpiresAt = now.Add(ttl)
		entry.LastHit = now
		entry.Size = rc.calculateSize(ruleset)
		
		// Move to front
		rc.lruList.MoveToFront(element)
	} else {
		// Create new entry
		entry := &CacheEntry{
			Key:       id,
			RuleSet:   ruleset,
			ExpiresAt: now.Add(ttl),
			CreatedAt: now,
			LastHit:   now,
			HitCount:  0,
			Size:      rc.calculateSize(ruleset),
		}
		
		// Add to front of LRU list
		element := rc.lruList.PushFront(entry)
		rc.cache[id] = element
		
		// Check if we need to evict
		rc.evictIfNecessary()
	}
	
	atomic.AddInt64(&rc.totalSets, 1)
}

// SetWithDefaultTTL stores a ruleset with the default TTL
func (rc *RuleCache) SetWithDefaultTTL(id string, ruleset *RuleSet) {
	rc.Set(id, ruleset, rc.defaultTTL)
}

// Delete removes a specific entry from the cache
func (rc *RuleCache) Delete(id string) bool {
	rc.mutex.Lock()
	defer rc.mutex.Unlock()
	
	if element, exists := rc.cache[id]; exists {
		rc.removeElement(element)
		return true
	}
	
	return false
}

// Clear removes all entries from the cache
func (rc *RuleCache) Clear() {
	rc.mutex.Lock()
	defer rc.mutex.Unlock()
	
	rc.cache = make(map[string]*list.Element)
	rc.lruList.Init()
}

// GetStats returns comprehensive cache statistics
func (rc *RuleCache) GetStats() CacheStats {
	rc.mutex.RLock()
	defer rc.mutex.RUnlock()
	
	hits := atomic.LoadInt64(&rc.hits)
	misses := atomic.LoadInt64(&rc.misses)
	total := hits + misses
	
	var hitRate float64
	if total > 0 {
		hitRate = float64(hits) / float64(total) * 100
	}
	
	var memoryUsage int64
	var totalHits int64
	var oldest, newest time.Time
	
	for element := rc.lruList.Back(); element != nil; element = element.Prev() {
		entry := element.Value.(*CacheEntry)
		memoryUsage += int64(entry.Size)
		totalHits += entry.HitCount
		
		if oldest.IsZero() || entry.CreatedAt.Before(oldest) {
			oldest = entry.CreatedAt
		}
		if newest.IsZero() || entry.CreatedAt.After(newest) {
			newest = entry.CreatedAt
		}
	}
	
	var averageHits float64
	if len(rc.cache) > 0 {
		averageHits = float64(totalHits) / float64(len(rc.cache))
	}
	
	return CacheStats{
		Size:          len(rc.cache),
		MaxSize:       rc.maxSize,
		Hits:          hits,
		Misses:        misses,
		HitRate:       hitRate,
		Evictions:     atomic.LoadInt64(&rc.evictions),
		Expired:       atomic.LoadInt64(&rc.expired),
		TotalSets:     atomic.LoadInt64(&rc.totalSets),
		MemoryUsage:   memoryUsage,
		AverageHits:   averageHits,
		OldestEntry:   oldest,
		NewestEntry:   newest,
		DefaultTTL:    rc.defaultTTL.String(),
	}
}

// GetKeys returns all keys currently in the cache
func (rc *RuleCache) GetKeys() []string {
	rc.mutex.RLock()
	defer rc.mutex.RUnlock()
	
	keys := make([]string, 0, len(rc.cache))
	for key := range rc.cache {
		keys = append(keys, key)
	}
	
	return keys
}

// GetExpiredKeys returns keys of entries that have expired
func (rc *RuleCache) GetExpiredKeys() []string {
	rc.mutex.RLock()
	defer rc.mutex.RUnlock()
	
	now := time.Now()
	var expiredKeys []string
	
	for key, element := range rc.cache {
		entry := element.Value.(*CacheEntry)
		if now.After(entry.ExpiresAt) {
			expiredKeys = append(expiredKeys, key)
		}
	}
	
	return expiredKeys
}

// Contains checks if a key exists in the cache (without affecting LRU order)
func (rc *RuleCache) Contains(id string) bool {
	rc.mutex.RLock()
	defer rc.mutex.RUnlock()
	
	element, exists := rc.cache[id]
	if !exists {
		return false
	}
	
	entry := element.Value.(*CacheEntry)
	return time.Now().Before(entry.ExpiresAt)
}

// GetSize returns current cache size
func (rc *RuleCache) GetSize() int {
	rc.mutex.RLock()
	defer rc.mutex.RUnlock()
	
	return len(rc.cache)
}

// GetMaxSize returns maximum cache size
func (rc *RuleCache) GetMaxSize() int {
	return rc.maxSize
}

// SetMaxSize updates the maximum cache size
func (rc *RuleCache) SetMaxSize(maxSize int) {
	rc.mutex.Lock()
	defer rc.mutex.Unlock()
	
	rc.maxSize = maxSize
	rc.evictIfNecessary()
}

// GetTTL returns the default TTL
func (rc *RuleCache) GetTTL() time.Duration {
	return rc.defaultTTL
}

// SetTTL updates the default TTL
func (rc *RuleCache) SetTTL(ttl time.Duration) {
	rc.defaultTTL = ttl
}

// Close stops the cache and cleanup goroutines
func (rc *RuleCache) Close() {
	close(rc.stopCleanup)
	if rc.cleanupTicker != nil {
		rc.cleanupTicker.Stop()
	}
}

// Private helper methods

func (rc *RuleCache) removeElement(element *list.Element) {
	entry := element.Value.(*CacheEntry)
	delete(rc.cache, entry.Key)
	rc.lruList.Remove(element)
}

func (rc *RuleCache) evictIfNecessary() {
	for len(rc.cache) > rc.maxSize {
		// Remove least recently used (back of list)
		oldest := rc.lruList.Back()
		if oldest != nil {
			rc.removeElement(oldest)
			atomic.AddInt64(&rc.evictions, 1)
		} else {
			break
		}
	}
}

func (rc *RuleCache) calculateSize(ruleset *RuleSet) int {
	// Simplified size calculation
	size := len(ruleset.ID) + len(ruleset.Version)
	
	for _, rule := range ruleset.Rules {
		size += len(rule.ID) + len(rule.Condition.Field) + len(rule.Condition.Operator)
		size += 100 // Approximate size for other fields
		
		for _, action := range rule.Actions {
			size += len(action.Type) + len(action.Target) + len(action.ID)
			size += 50 // Approximate size for params
		}
	}
	
	for name, service := range ruleset.ExternalServices {
		size += len(name) + len(service.URL)
		size += 50 // Approximate size for headers and auth
	}
	
	return size
}

func (rc *RuleCache) startCleanup() {
	rc.cleanupTicker = time.NewTicker(5 * time.Minute) // Cleanup every 5 minutes
	
	go func() {
		for {
			select {
			case <-rc.cleanupTicker.C:
				rc.cleanupExpired()
			case <-rc.stopCleanup:
				return
			}
		}
	}()
}

func (rc *RuleCache) cleanupExpired() {
	rc.mutex.Lock()
	defer rc.mutex.Unlock()
	
	now := time.Now()
	var toRemove []*list.Element
	
	// Collect expired entries
	for element := rc.lruList.Back(); element != nil; element = element.Prev() {
		entry := element.Value.(*CacheEntry)
		if now.After(entry.ExpiresAt) {
			toRemove = append(toRemove, element)
		}
	}
	
	// Remove expired entries
	for _, element := range toRemove {
		rc.removeElement(element)
		atomic.AddInt64(&rc.expired, 1)
	}
}

// Utility methods for debugging and monitoring

func (rc *RuleCache) GetEntryDetails(id string) (*CacheEntry, bool) {
	rc.mutex.RLock()
	defer rc.mutex.RUnlock()
	
	element, exists := rc.cache[id]
	if !exists {
		return nil, false
	}
	
	entry := element.Value.(*CacheEntry)
	
	// Create a copy to avoid race conditions
	entryCopy := &CacheEntry{
		Key:       entry.Key,
		RuleSet:   entry.RuleSet,
		ExpiresAt: entry.ExpiresAt,
		CreatedAt: entry.CreatedAt,
		LastHit:   entry.LastHit,
		HitCount:  entry.HitCount,
		Size:      entry.Size,
	}
	
	return entryCopy, true
}

func (rc *RuleCache) GetLRUOrder() []string {
	rc.mutex.RLock()
	defer rc.mutex.RUnlock()
	
	var keys []string
	for element := rc.lruList.Front(); element != nil; element = element.Next() {
		entry := element.Value.(*CacheEntry)
		keys = append(keys, entry.Key)
	}
	
	return keys
}

// Reset statistics
func (rc *RuleCache) ResetStats() {
	atomic.StoreInt64(&rc.hits, 0)
	atomic.StoreInt64(&rc.misses, 0)
	atomic.StoreInt64(&rc.evictions, 0)
	atomic.StoreInt64(&rc.expired, 0)
	atomic.StoreInt64(&rc.totalSets, 0)
}

// Example usage and testing
func main() {
	fmt.Println("Rule Cache Test Suite")
	fmt.Println("====================")
	
	// Create a cache with max size 3 and 10 second TTL for testing
	cache := NewRuleCache(3, 10*time.Second)
	defer cache.Close()
	
	// Create test rulesets
	ruleset1 := &RuleSet{
		ID:      "rules_v1",
		Version: "1.0.0",
		Rules: []Rule{
			{
				ID:       "rule1",
				Priority: 1,
				Condition: Condition{
					Field:    "user.age",
					Operator: ">=",
					Value:    18,
				},
				Actions: []Action{
					{
						Type:   "log",
						Target: "console",
					},
				},
			},
		},
	}
	
	ruleset2 := &RuleSet{
		ID:      "rules_v2",
		Version: "2.0.0",
		Rules: []Rule{
			{
				ID:       "rule2",
				Priority: 1,
				Condition: Condition{
					Field:    "user.status",
					Operator: "==",
					Value:    "active",
				},
				Actions: []Action{
					{
						Type:   "webhook",
						Target: "https://api.example.com/notify",
					},
				},
			},
		},
	}
	
	// Test 1: Basic set and get operations
	fmt.Println("\nTest 1: Basic Operations")
	fmt.Println("------------------------")
	
	cache.Set("test1", ruleset1, 5*time.Second)
	cache.Set("test2", ruleset2, 0) // Use default TTL
	
	if retrieved, found := cache.Get("test1"); found {
		fmt.Printf("✓ Retrieved ruleset: %s (version %s)\n", retrieved.ID, retrieved.Version)
	} else {
		fmt.Println("✗ Failed to retrieve test1")
	}
	
	// Test 2: Cache statistics
	fmt.Println("\nTest 2: Cache Statistics")
	fmt.Println("------------------------")
	
	stats := cache.GetStats()
	fmt.Printf("Cache Size: %d/%d\n", stats.Size, stats.MaxSize)
	fmt.Printf("Hits: %d, Misses: %d\n", stats.Hits, stats.Misses)
	fmt.Printf("Hit Rate: %.2f%%\n", stats.HitRate)
	fmt.Printf("Memory Usage: %d bytes\n", stats.MemoryUsage)
	
	// Test 3: LRU eviction
	fmt.Println("\nTest 3: LRU Eviction")
	fmt.Println("--------------------")
	
	// Fill cache beyond capacity
	cache.Set("item1", ruleset1, 30*time.Second)
	cache.Set("item2", ruleset2, 30*time.Second)
	cache.Set("item3", ruleset1, 30*time.Second)
	cache.Set("item4", ruleset2, 30*time.Second) // Should evict oldest
	
	lruOrder := cache.GetLRUOrder()
	fmt.Printf("LRU Order (most to least recent): %v\n", lruOrder)
	
	// Check which items are still in cache
	for _, key := range []string{"item1", "item2", "item3", "item4"} {
		if cache.Contains(key) {
			fmt.Printf("✓ %s is in cache\n", key)
		} else {
			fmt.Printf("✗ %s was evicted\n", key)
		}
	}
	
	// Test 4: TTL expiration
	fmt.Println("\nTest 4: TTL Expiration")
	fmt.Println("----------------------")
	
	cache.Set("short_lived", ruleset1, 1*time.Second)
	
	if cache.Contains("short_lived") {
		fmt.Println("✓ short_lived item exists")
	}
	
	time.Sleep(2 * time.Second)
	
	if !cache.Contains("short_lived") {
		fmt.Println("✓ short_lived item expired as expected")
	} else {
		fmt.Println("✗ short_lived item should have expired")
	}
	
	// Test 5: Concurrent access
	fmt.Println("\nTest 5: Concurrent Access")
	fmt.Println("-------------------------")
	
	var wg sync.WaitGroup
	concurrentOps := 100
	
	// Concurrent writes
	for i := 0; i < concurrentOps; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			key := fmt.Sprintf("concurrent_%d", id)
			cache.Set(key, ruleset1, 30*time.Second)
		}(i)
	}
	
	// Concurrent reads
	for i := 0; i < concurrentOps; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			key := fmt.Sprintf("concurrent_%d", id%10) // Read existing keys
			cache.Get(key)
		}(i)
	}
	
	wg.Wait()
	
	finalStats := cache.GetStats()
	fmt.Printf("After concurrent operations:\n")
	fmt.Printf("  Cache Size: %d/%d\n", finalStats.Size, finalStats.MaxSize)
	fmt.Printf("  Total Operations: %d\n", finalStats.Hits+finalStats.Misses)
	fmt.Printf("  Hit Rate: %.2f%%\n", finalStats.HitRate)
	fmt.Printf("  Evictions: %d\n", finalStats.Evictions)
	
	// Test 6: Entry details
	fmt.Println("\nTest 6: Entry Details")
	fmt.Println("---------------------")
	
	cache.Set("detailed_test", ruleset1, 1*time.Minute)
	
	// Access it a few times to increase hit count
	for i := 0; i < 5; i++ {
		cache.Get("detailed_test")
	}
	
	if entry, found := cache.GetEntryDetails("detailed_test"); found {
		fmt.Printf("Entry Details for 'detailed_test':\n")
		fmt.Printf("  Created: %v\n", entry.CreatedAt.Format(time.RFC3339))
		fmt.Printf("  Last Hit: %v\n", entry.LastHit.Format(time.RFC3339))
		fmt.Printf("  Hit Count: %d\n", entry.HitCount)
		fmt.Printf("  Size: %d bytes\n", entry.Size)
		fmt.Printf("  Expires: %v\n", entry.ExpiresAt.Format(time.RFC3339))
	}
	
	fmt.Println("\n" + "="*50)
	fmt.Println("All tests completed successfully!")
	fmt.Println("="*50)
}