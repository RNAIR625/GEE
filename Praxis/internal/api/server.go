package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"praxis/internal/config"
	"praxis/internal/db"

	"github.com/gorilla/mux"
)

type Server struct {
	config    *config.Config
	dbManager *db.Manager
}

func NewServer(cfg *config.Config, dbManager *db.Manager) *Server {
	return &Server{
		config:    cfg,
		dbManager: dbManager,
	}
}

func (s *Server) Router() http.Handler {
	r := mux.NewRouter()

	// API routes
	api := r.PathPrefix("/api/v1").Subrouter()
	
	// Database upload endpoint
	api.HandleFunc("/database/upload", s.handleDatabaseUpload).Methods("POST")
	
	// Data retrieval endpoints
	api.HandleFunc("/field-classes", s.handleGetFieldClasses).Methods("GET")
	api.HandleFunc("/fields", s.handleGetFields).Methods("GET")
	api.HandleFunc("/flow-definitions", s.handleGetFlowDefinitions).Methods("GET")
	
	// Status endpoints
	api.HandleFunc("/health", s.handleHealth).Methods("GET")
	api.HandleFunc("/status", s.handleStatus).Methods("GET")

	// Add CORS middleware
	r.Use(corsMiddleware)

	return r
}

// handleDatabaseUpload handles SQLite database file upload
func (s *Server) handleDatabaseUpload(w http.ResponseWriter, r *http.Request) {
	// Parse multipart form
	err := r.ParseMultipartForm(100 << 20) // 100 MB max
	if err != nil {
		http.Error(w, "Failed to parse form", http.StatusBadRequest)
		return
	}

	// Get file from form
	file, header, err := r.FormFile("database")
	if err != nil {
		http.Error(w, "Failed to get file from form", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Save database
	if err := s.dbManager.SaveDatabase(file, header.Filename); err != nil {
		http.Error(w, fmt.Sprintf("Failed to save database: %v", err), http.StatusInternalServerError)
		return
	}

	// Return success response
	response := map[string]interface{}{
		"success": true,
		"message": "Database uploaded successfully",
		"filename": header.Filename,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleGetFieldClasses returns all field classes
func (s *Server) handleGetFieldClasses(w http.ResponseWriter, r *http.Request) {
	classes, err := s.dbManager.GetFieldClasses()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get field classes: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    classes,
		"count":   len(classes),
	})
}

// handleGetFields returns all fields
func (s *Server) handleGetFields(w http.ResponseWriter, r *http.Request) {
	fields, err := s.dbManager.GetFields()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get fields: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    fields,
		"count":   len(fields),
	})
}

// handleGetFlowDefinitions returns all flow definitions
func (s *Server) handleGetFlowDefinitions(w http.ResponseWriter, r *http.Request) {
	flows, err := s.dbManager.GetFlowDefinitions()
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to get flow definitions: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    flows,
		"count":   len(flows),
	})
}

// handleHealth returns server health status
func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status": "healthy",
		"service": "praxis",
	})
}

// handleStatus returns detailed server status
func (s *Server) handleStatus(w http.ResponseWriter, r *http.Request) {
	status := s.dbManager.GetStatus()
	status["server"] = map[string]interface{}{
		"host": s.config.Server.Host,
		"port": s.config.Server.Port,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

// corsMiddleware adds CORS headers
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}