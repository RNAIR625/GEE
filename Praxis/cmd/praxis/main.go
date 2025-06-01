package main

import (
	"fmt"
	"log"
	"net/http"
	"praxis/internal/api"
	"praxis/internal/config"
	"praxis/internal/db"
)

func main() {
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
	log.Printf("Praxis server starting on %s", addr)
	
	if err := http.ListenAndServe(addr, server.Router()); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}