package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// ExternalClient manages HTTP requests to external services
type ExternalClient struct {
	client      *http.Client
	baseURL     string
	timeout     time.Duration
	retryConfig RetryConfig
	metrics     *ClientMetrics
	mutex       sync.RWMutex
}

// ServiceCall represents a service call configuration
type ServiceCall struct {
	Method   string                 `json:"method"`
	Endpoint string                 `json:"endpoint"`
	Headers  map[string]string      `json:"headers"`
	Body     map[string]interface{} `json:"body,omitempty"`
	Timeout  time.Duration          `json:"timeout"`
	Retries  int                    `json:"retries,omitempty"`
}

// RetryConfig defines retry behavior
type RetryConfig struct {
	MaxRetries    int           `json:"max_retries"`
	InitialDelay  time.Duration `json:"initial_delay"`
	MaxDelay      time.Duration `json:"max_delay"`
	BackoffFactor float64       `json:"backoff_factor"`
	RetryableStatusCodes []int  `json:"retryable_status_codes"`
}

// ClientMetrics tracks client performance
type ClientMetrics struct {
	TotalRequests    int64         `json:"total_requests"`
	SuccessfulCalls  int64         `json:"successful_calls"`
	FailedCalls      int64         `json:"failed_calls"`
	TimeoutErrors    int64         `json:"timeout_errors"`
	RetryAttempts    int64         `json:"retry_attempts"`
	AverageLatency   time.Duration `json:"average_latency"`
	TotalLatency     int64         `json:"total_latency_ns"`
	ConnectionErrors int64         `json:"connection_errors"`
	JSONErrors       int64         `json:"json_errors"`
}

// ServiceResponse wraps HTTP response with additional metadata
type ServiceResponse struct {
	StatusCode    int                    `json:"status_code"`
	Headers       map[string][]string    `json:"headers"`
	Body          map[string]interface{} `json:"body,omitempty"`
	RawBody       []byte                 `json:"raw_body,omitempty"`
	Latency       time.Duration          `json:"latency"`
	Attempts      int                    `json:"attempts"`
	Success       bool                   `json:"success"`
	Error         string                 `json:"error,omitempty"`
}

// ClientConfig allows detailed client configuration
type ClientConfig struct {
	BaseURL           string        `json:"base_url"`
	Timeout           time.Duration `json:"timeout"`
	MaxIdleConns      int           `json:"max_idle_conns"`
	MaxConnsPerHost   int           `json:"max_conns_per_host"`
	IdleConnTimeout   time.Duration `json:"idle_conn_timeout"`
	TLSHandshakeTimeout time.Duration `json:"tls_handshake_timeout"`
	InsecureSkipVerify bool         `json:"insecure_skip_verify"`
	RetryConfig       RetryConfig   `json:"retry_config"`
}

// NewExternalClient creates a new HTTP client with connection pooling
func NewExternalClient(baseURL string, timeout time.Duration) *ExternalClient {
	config := ClientConfig{
		BaseURL:             baseURL,
		Timeout:             timeout,
		MaxIdleConns:        100,
		MaxConnsPerHost:     10,
		IdleConnTimeout:     90 * time.Second,
		TLSHandshakeTimeout: 10 * time.Second,
		InsecureSkipVerify:  false,
		RetryConfig: RetryConfig{
			MaxRetries:    3,
			InitialDelay:  100 * time.Millisecond,
			MaxDelay:      5 * time.Second,
			BackoffFactor: 2.0,
			RetryableStatusCodes: []int{408, 429, 502, 503, 504},
		},
	}
	
	return NewExternalClientWithConfig(config)
}

// NewExternalClientWithConfig creates a client with detailed configuration
func NewExternalClientWithConfig(config ClientConfig) *ExternalClient {
	// Configure transport with connection pooling
	transport := &http.Transport{
		MaxIdleConns:        config.MaxIdleConns,
		MaxIdleConnsPerHost: config.MaxConnsPerHost,
		IdleConnTimeout:     config.IdleConnTimeout,
		TLSHandshakeTimeout: config.TLSHandshakeTimeout,
		DialContext: (&net.Dialer{
			Timeout:   30 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: config.InsecureSkipVerify,
		},
	}
	
	// Create HTTP client
	httpClient := &http.Client{
		Transport: transport,
		Timeout:   config.Timeout,
	}
	
	return &ExternalClient{
		client:      httpClient,
		baseURL:     strings.TrimRight(config.BaseURL, "/"),
		timeout:     config.Timeout,
		retryConfig: config.RetryConfig,
		metrics:     &ClientMetrics{},
	}
}

// ExecuteCall executes a service call with retry logic
func (ec *ExternalClient) ExecuteCall(call ServiceCall) (*ServiceResponse, error) {
	start := time.Now()
	atomic.AddInt64(&ec.metrics.TotalRequests, 1)
	
	var lastErr error
	maxRetries := call.Retries
	if maxRetries == 0 {
		maxRetries = ec.retryConfig.MaxRetries
	}
	
	for attempt := 0; attempt <= maxRetries; attempt++ {
		if attempt > 0 {
			// Calculate backoff delay
			delay := ec.calculateBackoffDelay(attempt)
			time.Sleep(delay)
			atomic.AddInt64(&ec.metrics.RetryAttempts, 1)
		}
		
		response, err := ec.executeRequest(call)
		if err == nil && !ec.shouldRetry(response.StatusCode) {
			// Success
			response.Attempts = attempt + 1
			response.Latency = time.Since(start)
			response.Success = true
			
			ec.updateMetrics(true, response.Latency, err)
			return response, nil
		}
		
		lastErr = err
		if err != nil && !ec.isRetryableError(err) {
			// Non-retryable error
			break
		}
		
		if response != nil && !ec.shouldRetry(response.StatusCode) {
			// Non-retryable status code
			response.Attempts = attempt + 1
			response.Latency = time.Since(start)
			response.Success = false
			response.Error = fmt.Sprintf("HTTP %d", response.StatusCode)
			
			ec.updateMetrics(false, response.Latency, lastErr)
			return response, fmt.Errorf("HTTP %d: request failed", response.StatusCode)
		}
	}
	
	// All retries exhausted
	totalLatency := time.Since(start)
	ec.updateMetrics(false, totalLatency, lastErr)
	
	response := &ServiceResponse{
		Attempts: maxRetries + 1,
		Latency:  totalLatency,
		Success:  false,
		Error:    fmt.Sprintf("max retries exceeded: %v", lastErr),
	}
	
	return response, fmt.Errorf("max retries (%d) exceeded: %w", maxRetries, lastErr)
}

// executeRequest performs a single HTTP request
func (ec *ExternalClient) executeRequest(call ServiceCall) (*ServiceResponse, error) {
	// Build URL
	url := ec.buildURL(call.Endpoint)
	
	// Prepare request body
	var requestBody io.Reader
	if call.Body != nil && (call.Method == "POST" || call.Method == "PUT" || call.Method == "PATCH") {
		jsonBody, err := json.Marshal(call.Body)
		if err != nil {
			atomic.AddInt64(&ec.metrics.JSONErrors, 1)
			return nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		requestBody = bytes.NewReader(jsonBody)
	}
	
	// Create request
	ctx := context.Background()
	if call.Timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, call.Timeout)
		defer cancel()
	}
	
	req, err := http.NewRequestWithContext(ctx, call.Method, url, requestBody)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	
	// Set headers
	ec.setDefaultHeaders(req)
	for key, value := range call.Headers {
		req.Header.Set(key, value)
	}
	
	// Execute request
	resp, err := ec.client.Do(req)
	if err != nil {
		if ec.isTimeoutError(err) {
			atomic.AddInt64(&ec.metrics.TimeoutErrors, 1)
		} else if ec.isConnectionError(err) {
			atomic.AddInt64(&ec.metrics.ConnectionErrors, 1)
		}
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()
	
	// Read response body
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}
	
	// Parse JSON response if applicable
	var bodyMap map[string]interface{}
	if len(bodyBytes) > 0 && ec.isJSONResponse(resp) {
		if err := json.Unmarshal(bodyBytes, &bodyMap); err != nil {
			atomic.AddInt64(&ec.metrics.JSONErrors, 1)
			// Don't fail the request, just log the JSON error
			bodyMap = map[string]interface{}{
				"raw_response": string(bodyBytes),
				"json_error":   err.Error(),
			}
		}
	}
	
	return &ServiceResponse{
		StatusCode: resp.StatusCode,
		Headers:    resp.Header,
		Body:       bodyMap,
		RawBody:    bodyBytes,
	}, nil
}

// GetJSON performs a GET request and returns JSON response
func (ec *ExternalClient) GetJSON(endpoint string) (map[string]interface{}, error) {
	call := ServiceCall{
		Method:   "GET",
		Endpoint: endpoint,
		Headers:  map[string]string{"Accept": "application/json"},
	}
	
	response, err := ec.ExecuteCall(call)
	if err != nil {
		return nil, err
	}
	
	if response.Body == nil {
		return make(map[string]interface{}), nil
	}
	
	return response.Body, nil
}

// PostJSON performs a POST request with JSON body and returns JSON response
func (ec *ExternalClient) PostJSON(endpoint string, data interface{}) (map[string]interface{}, error) {
	var body map[string]interface{}
	
	// Convert data to map[string]interface{}
	if data != nil {
		jsonBytes, err := json.Marshal(data)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request data: %w", err)
		}
		
		if err := json.Unmarshal(jsonBytes, &body); err != nil {
			return nil, fmt.Errorf("failed to convert data to map: %w", err)
		}
	}
	
	call := ServiceCall{
		Method:   "POST",
		Endpoint: endpoint,
		Headers: map[string]string{
			"Content-Type": "application/json",
			"Accept":       "application/json",
		},
		Body: body,
	}
	
	response, err := ec.ExecuteCall(call)
	if err != nil {
		return nil, err
	}
	
	if response.Body == nil {
		return make(map[string]interface{}), nil
	}
	
	return response.Body, nil
}

// PutJSON performs a PUT request with JSON body
func (ec *ExternalClient) PutJSON(endpoint string, data interface{}) (map[string]interface{}, error) {
	var body map[string]interface{}
	
	if data != nil {
		jsonBytes, err := json.Marshal(data)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request data: %w", err)
		}
		
		if err := json.Unmarshal(jsonBytes, &body); err != nil {
			return nil, fmt.Errorf("failed to convert data to map: %w", err)
		}
	}
	
	call := ServiceCall{
		Method:   "PUT",
		Endpoint: endpoint,
		Headers: map[string]string{
			"Content-Type": "application/json",
			"Accept":       "application/json",
		},
		Body: body,
	}
	
	response, err := ec.ExecuteCall(call)
	if err != nil {
		return nil, err
	}
	
	if response.Body == nil {
		return make(map[string]interface{}), nil
	}
	
	return response.Body, nil
}

// DeleteJSON performs a DELETE request
func (ec *ExternalClient) DeleteJSON(endpoint string) (map[string]interface{}, error) {
	call := ServiceCall{
		Method:   "DELETE",
		Endpoint: endpoint,
		Headers:  map[string]string{"Accept": "application/json"},
	}
	
	response, err := ec.ExecuteCall(call)
	if err != nil {
		return nil, err
	}
	
	if response.Body == nil {
		return make(map[string]interface{}), nil
	}
	
	return response.Body, nil
}

// Helper methods

func (ec *ExternalClient) buildURL(endpoint string) string {
	endpoint = strings.TrimLeft(endpoint, "/")
	if ec.baseURL == "" {
		return endpoint
	}
	return fmt.Sprintf("%s/%s", ec.baseURL, endpoint)
}

func (ec *ExternalClient) setDefaultHeaders(req *http.Request) {
	req.Header.Set("User-Agent", "ExternalClient/1.0")
	if req.Header.Get("Content-Type") == "" && req.Body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
}

func (ec *ExternalClient) isJSONResponse(resp *http.Response) bool {
	contentType := resp.Header.Get("Content-Type")
	return strings.Contains(strings.ToLower(contentType), "application/json")
}

func (ec *ExternalClient) shouldRetry(statusCode int) bool {
	for _, code := range ec.retryConfig.RetryableStatusCodes {
		if statusCode == code {
			return true
		}
	}
	return false
}

func (ec *ExternalClient) isRetryableError(err error) bool {
	if err == nil {
		return false
	}
	
	// Check for timeout errors
	if ec.isTimeoutError(err) {
		return true
	}
	
	// Check for connection errors
	if ec.isConnectionError(err) {
		return true
	}
	
	// Check for temporary errors
	if netErr, ok := err.(net.Error); ok {
		return netErr.Temporary()
	}
	
	return false
}

func (ec *ExternalClient) isTimeoutError(err error) bool {
	if err == nil {
		return false
	}
	
	// Check for context timeout
	if err == context.DeadlineExceeded {
		return true
	}
	
	// Check for net.Error timeout
	if netErr, ok := err.(net.Error); ok {
		return netErr.Timeout()
	}
	
	// Check error message for timeout indicators
	errMsg := strings.ToLower(err.Error())
	return strings.Contains(errMsg, "timeout") || strings.Contains(errMsg, "deadline exceeded")
}

func (ec *ExternalClient) isConnectionError(err error) bool {
	if err == nil {
		return false
	}
	
	errMsg := strings.ToLower(err.Error())
	connectionErrors := []string{
		"connection refused",
		"connection reset",
		"no route to host",
		"network unreachable",
		"host unreachable",
	}
	
	for _, connErr := range connectionErrors {
		if strings.Contains(errMsg, connErr) {
			return true
		}
	}
	
	return false
}

func (ec *ExternalClient) calculateBackoffDelay(attempt int) time.Duration {
	delay := float64(ec.retryConfig.InitialDelay) * 
		(ec.retryConfig.BackoffFactor * float64(attempt-1))
	
	if delay > float64(ec.retryConfig.MaxDelay) {
		delay = float64(ec.retryConfig.MaxDelay)
	}
	
	return time.Duration(delay)
}

func (ec *ExternalClient) updateMetrics(success bool, latency time.Duration, err error) {
	if success {
		atomic.AddInt64(&ec.metrics.SuccessfulCalls, 1)
	} else {
		atomic.AddInt64(&ec.metrics.FailedCalls, 1)
	}
	
	// Update latency metrics
	atomic.AddInt64(&ec.metrics.TotalLatency, latency.Nanoseconds())
	
	// Calculate average latency
	totalRequests := atomic.LoadInt64(&ec.metrics.TotalRequests)
	if totalRequests > 0 {
		avgLatencyNs := atomic.LoadInt64(&ec.metrics.TotalLatency) / totalRequests
		ec.metrics.AverageLatency = time.Duration(avgLatencyNs)
	}
}

// GetMetrics returns current client metrics
func (ec *ExternalClient) GetMetrics() ClientMetrics {
	ec.mutex.RLock()
	defer ec.mutex.RUnlock()
	
	return ClientMetrics{
		TotalRequests:    atomic.LoadInt64(&ec.metrics.TotalRequests),
		SuccessfulCalls:  atomic.LoadInt64(&ec.metrics.SuccessfulCalls),
		FailedCalls:      atomic.LoadInt64(&ec.metrics.FailedCalls),
		TimeoutErrors:    atomic.LoadInt64(&ec.metrics.TimeoutErrors),
		RetryAttempts:    atomic.LoadInt64(&ec.metrics.RetryAttempts),
		AverageLatency:   ec.metrics.AverageLatency,
		TotalLatency:     atomic.LoadInt64(&ec.metrics.TotalLatency),
		ConnectionErrors: atomic.LoadInt64(&ec.metrics.ConnectionErrors),
		JSONErrors:       atomic.LoadInt64(&ec.metrics.JSONErrors),
	}
}

// ResetMetrics clears all metrics
func (ec *ExternalClient) ResetMetrics() {
	ec.mutex.Lock()
	defer ec.mutex.Unlock()
	
	atomic.StoreInt64(&ec.metrics.TotalRequests, 0)
	atomic.StoreInt64(&ec.metrics.SuccessfulCalls, 0)
	atomic.StoreInt64(&ec.metrics.FailedCalls, 0)
	atomic.StoreInt64(&ec.metrics.TimeoutErrors, 0)
	atomic.StoreInt64(&ec.metrics.RetryAttempts, 0)
	atomic.StoreInt64(&ec.metrics.TotalLatency, 0)
	atomic.StoreInt64(&ec.metrics.ConnectionErrors, 0)
	atomic.StoreInt64(&ec.metrics.JSONErrors, 0)
	ec.metrics.AverageLatency = 0
}

// Close properly shuts down the client
func (ec *ExternalClient) Close() {
	if transport, ok := ec.client.Transport.(*http.Transport); ok {
		transport.CloseIdleConnections()
	}
}

// MockServer for testing (simple HTTP server)
type MockServer struct {
	server *http.Server
	port   int
}

func NewMockServer(port int) *MockServer {
	mux := http.NewServeMux()
	
	// Success endpoint
	mux.HandleFunc("/success", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status":  "success",
			"message": "Request successful",
			"method":  r.Method,
		})
	})
	
	// Error endpoint
	mux.HandleFunc("/error", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status": "error",
			"message": "Internal server error",
		})
	})
	
	// Timeout endpoint
	mux.HandleFunc("/timeout", func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(2 * time.Second) // Longer than typical timeout
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status": "delayed",
		})
	})
	
	// Retry endpoint (fails first 2 times, succeeds on 3rd)
	var attemptCount int32
	mux.HandleFunc("/retry", func(w http.ResponseWriter, r *http.Request) {
		count := atomic.AddInt32(&attemptCount, 1)
		if count <= 2 {
			w.WriteHeader(http.StatusServiceUnavailable)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"status": "unavailable",
				"attempt": count,
			})
		} else {
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"status": "success",
				"attempt": count,
			})
		}
	})
	
	server := &http.Server{
		Addr:    fmt.Sprintf(":%d", port),
		Handler: mux,
	}
	
	return &MockServer{
		server: server,
		port:   port,
	}
}

func (ms *MockServer) Start() error {
	go func() {
		if err := ms.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			fmt.Printf("Mock server error: %v\n", err)
		}
	}()
	
	// Wait for server to start
	time.Sleep(100 * time.Millisecond)
	return nil
}

func (ms *MockServer) Stop() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return ms.server.Shutdown(ctx)
}

// Example usage and testing
func main() {
	fmt.Println("External Service Client Test Suite")
	fmt.Println("==================================")
	
	// Start mock server for testing
	mockServer := NewMockServer(8080)
	if err := mockServer.Start(); err != nil {
		fmt.Printf("Failed to start mock server: %v\n", err)
		return
	}
	defer mockServer.Stop()
	
	// Create client
	client := NewExternalClient("http://localhost:8080", 1*time.Second)
	defer client.Close()
	
	// Test 1: Successful GET request
	fmt.Println("\nTest 1: Successful GET Request")
	fmt.Println("------------------------------")
	
	response, err := client.GetJSON("/success")
	if err != nil {
		fmt.Printf("✗ GET request failed: %v\n", err)
	} else {
		fmt.Printf("✓ GET request successful: %v\n", response)
	}
	
	// Test 2: Successful POST request
	fmt.Println("\nTest 2: Successful POST Request")
	fmt.Println("-------------------------------")
	
	postData := map[string]interface{}{
		"user_id": 123,
		"action":  "test",
	}
	
	response, err = client.PostJSON("/success", postData)
	if err != nil {
		fmt.Printf("✗ POST request failed: %v\n", err)
	} else {
		fmt.Printf("✓ POST request successful: %v\n", response)
	}
	
	// Test 3: Error handling
	fmt.Println("\nTest 3: Error Handling")
	fmt.Println("----------------------")
	
	response, err = client.GetJSON("/error")
	if err != nil {
		fmt.Printf("✓ Error correctly handled: %v\n", err)
	} else {
		fmt.Printf("✗ Should have failed: %v\n", response)
	}
	
	// Test 4: Timeout handling
	fmt.Println("\nTest 4: Timeout Handling")
	fmt.Println("------------------------")
	
	shortTimeoutCall := ServiceCall{
		Method:   "GET",
		Endpoint: "/timeout",
		Timeout:  500 * time.Millisecond, // Shorter than server delay
	}
	
	_, err = client.ExecuteCall(shortTimeoutCall)
	if err != nil {
		fmt.Printf("✓ Timeout correctly handled: %v\n", err)
	} else {
		fmt.Printf("✗ Should have timed out\n")
	}
	
	// Test 5: Retry logic
	fmt.Println("\nTest 5: Retry Logic")
	fmt.Println("-------------------")
	
	retryCall := ServiceCall{
		Method:   "GET",
		Endpoint: "/retry",
		Retries:  3,
	}
	
	retryResponse, err := client.ExecuteCall(retryCall)
	if err != nil {
		fmt.Printf("✗ Retry failed: %v\n", err)
	} else {
		fmt.Printf("✓ Retry successful after %d attempts: %v\n", 
			retryResponse.Attempts, retryResponse.Body)
	}
	
	// Test 6: Connection error simulation
	fmt.Println("\nTest 6: Connection Error")
	fmt.Println("------------------------")
	
	badClient := NewExternalClient("http://localhost:9999", 1*time.Second)
	defer badClient.Close()
	
	_, err = badClient.GetJSON("/test")
	if err != nil {
		fmt.Printf("✓ Connection error correctly handled: %v\n", err)
	} else {
		fmt.Printf("✗ Should have failed with connection error\n")
	}
	
	// Test 7: Client metrics
	fmt.Println("\nTest 7: Client Metrics")
	fmt.Println("----------------------")
	
	metrics := client.GetMetrics()
	fmt.Printf("Total Requests: %d\n", metrics.TotalRequests)
	fmt.Printf("Successful Calls: %d\n", metrics.SuccessfulCalls)
	fmt.Printf("Failed Calls: %d\n", metrics.FailedCalls)
	fmt.Printf("Timeout Errors: %d\n", metrics.TimeoutErrors)
	fmt.Printf("Retry Attempts: %d\n", metrics.RetryAttempts)
	fmt.Printf("Average Latency: %v\n", metrics.AverageLatency)
	fmt.Printf("Connection Errors: %d\n", metrics.ConnectionErrors)
	fmt.Printf("JSON Errors: %d\n", metrics.JSONErrors)
	
	successRate := float64(metrics.SuccessfulCalls) / float64(metrics.TotalRequests) * 100
	fmt.Printf("Success Rate: %.2f%%\n", successRate)
	
	// Test 8: Concurrent requests
	fmt.Println("\nTest 8: Concurrent Requests")
	fmt.Println("---------------------------")
	
	var wg sync.WaitGroup
	concurrentRequests := 10
	
	start := time.Now()
	for i := 0; i < concurrentRequests; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			_, err := client.GetJSON("/success")
			if err != nil {
				fmt.Printf("Concurrent request %d failed: %v\n", id, err)
			}
		}(i)
	}
	
	wg.Wait()
	duration := time.Since(start)
	
	fmt.Printf("✓ %d concurrent requests completed in %v\n", concurrentRequests, duration)
	
	// Final metrics
	finalMetrics := client.GetMetrics()
	fmt.Printf("\nFinal Metrics Summary:\n")
	fmt.Printf("======================\n")
	fmt.Printf("Total Requests: %d\n", finalMetrics.TotalRequests)
	fmt.Printf("Success Rate: %.2f%%\n", 
		float64(finalMetrics.SuccessfulCalls)/float64(finalMetrics.TotalRequests)*100)
	fmt.Printf("Average Latency: %v\n", finalMetrics.AverageLatency)
}