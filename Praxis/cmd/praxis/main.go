package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"github.com/GEE/Praxis/internal/api"
	"github.com/GEE/Praxis/internal/config"
	"github.com/GEE/Praxis/internal/db"
	"github.com/GEE/Praxis/internal/debug"
)

func main() {
	// Parse command line flags
	debugFlag := flag.Bool("debug", false, "Enable debug mode with detailed logging")
	flag.Parse()

	// Set debug mode environment variable if flag is provided
	if *debugFlag {
		os.Setenv("GEE_DEBUG_MODE", "true")
		debug.LogDebug("startup", "Praxis starting in DEBUG mode", map[string]interface{}{
			"version": "1.0.0",
			"debug_enabled": true,
		})
	}

	// Load configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Initialize database manager
	dbManager := db.NewManager(cfg.Database.StoragePath)

	// Create API server
	server := api.NewServer(cfg, dbManager)

	// Start server
	addr := fmt.Sprintf(":%d", cfg.Server.Port)
	if debug.IsDebugMode() {
		debug.LogDebug("startup", "Praxis server starting", map[string]interface{}{
			"address": addr,
			"debug_mode": true,
		})
	}
	log.Printf("Praxis server starting on %s", addr)
	
	if err := http.ListenAndServe(addr, server.Router()); err != nil {
		if debug.IsDebugMode() {
			debug.LogError("Server failed to start", err, map[string]interface{}{
				"address": addr,
			})
		}
		log.Fatalf("Server failed to start: %v", err)
	}
}