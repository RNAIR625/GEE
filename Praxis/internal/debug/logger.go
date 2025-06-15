package debug

import (
	"encoding/json"
	"log"
	"os"
	"runtime"
	"time"
)

type DebugLogger struct {
	enabled bool
	logger  *log.Logger
}

type FunctionCall struct {
	Timestamp    string                 `json:"timestamp"`
	Function     string                 `json:"function"`
	Module       string                 `json:"module"`
	Input        map[string]interface{} `json:"input,omitempty"`
	Output       interface{}            `json:"output,omitempty"`
	Error        string                 `json:"error,omitempty"`
	DurationMs   float64                `json:"duration_ms"`
	Success      bool                   `json:"success"`
	DebugCategory string                `json:"debug_category"`
}

type SQLQuery struct {
	Timestamp     string  `json:"timestamp"`
	Query         string  `json:"sql_query"`
	ArgsCount     int     `json:"query_args_count"`
	QueryType     string  `json:"query_type"`
	ResultCount   int     `json:"result_count,omitempty"`
	DurationMs    float64 `json:"duration_ms"`
	Error         string  `json:"error,omitempty"`
	DebugCategory string  `json:"debug_category"`
}

var globalDebugLogger *DebugLogger

func init() {
	globalDebugLogger = NewDebugLogger()
}

func NewDebugLogger() *DebugLogger {
	enabled := isDebugMode()
	
	logger := log.New(os.Stdout, "", 0)
	if enabled {
		// Create debug log file
		file, err := os.OpenFile("../logs/praxis_debug.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
		if err == nil {
			logger = log.New(file, "", 0)
		}
	}
	
	return &DebugLogger{
		enabled: enabled,
		logger:  logger,
	}
}

func isDebugMode() bool {
	debugMode := os.Getenv("GEE_DEBUG_MODE")
	return debugMode == "true" || debugMode == "1" || debugMode == "yes" || debugMode == "on"
}

func IsDebugMode() bool {
	return globalDebugLogger.enabled
}

func LogFunctionCall(functionName string, input map[string]interface{}, fn func() (interface{}, error)) (interface{}, error) {
	if !globalDebugLogger.enabled {
		return fn()
	}
	
	start := time.Now()
	
	// Get caller info
	pc, file, _, _ := runtime.Caller(1)
	funcDetail := runtime.FuncForPC(pc)
	module := file
	if funcDetail != nil {
		module = funcDetail.Name()
	}
	
	result, err := fn()
	duration := time.Since(start)
	
	call := FunctionCall{
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
		Function:      functionName,
		Module:        module,
		Input:         input,
		DurationMs:    float64(duration.Nanoseconds()) / 1e6,
		Success:       err == nil,
		DebugCategory: "function_calls",
	}
	
	if err != nil {
		call.Error = err.Error()
	} else {
		call.Output = result
	}
	
	logEntry, _ := json.Marshal(call)
	globalDebugLogger.logger.Printf("%s", logEntry)
	
	return result, err
}

func LogSQL(query string, argsCount int, resultCount int, duration time.Duration, err error) {
	if !globalDebugLogger.enabled {
		return
	}
	
	// Determine query type
	queryType := "UNKNOWN"
	if len(query) > 0 {
		switch query[0] {
		case 'S', 's':
			queryType = "SELECT"
		case 'I', 'i':
			queryType = "INSERT"
		case 'U', 'u':
			queryType = "UPDATE"
		case 'D', 'd':
			queryType = "DELETE"
		case 'C', 'c':
			queryType = "CREATE"
		case 'A', 'a':
			queryType = "ALTER"
		}
	}
	
	sqlLog := SQLQuery{
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
		Query:         query,
		ArgsCount:     argsCount,
		QueryType:     queryType,
		ResultCount:   resultCount,
		DurationMs:    float64(duration.Nanoseconds()) / 1e6,
		DebugCategory: "sql",
	}
	
	if err != nil {
		sqlLog.Error = err.Error()
	}
	
	logEntry, _ := json.Marshal(sqlLog)
	globalDebugLogger.logger.Printf("%s", logEntry)
}

func LogDebug(category string, message string, details map[string]interface{}) {
	if !globalDebugLogger.enabled {
		return
	}
	
	logData := map[string]interface{}{
		"timestamp":      time.Now().UTC().Format(time.RFC3339),
		"level":          "DEBUG",
		"message":        message,
		"debug_category": category,
		"service":        "praxis",
	}
	
	for k, v := range details {
		logData[k] = v
	}
	
	logEntry, _ := json.Marshal(logData)
	globalDebugLogger.logger.Printf("%s", logEntry)
}

func LogError(message string, err error, details map[string]interface{}) {
	if !globalDebugLogger.enabled {
		return
	}
	
	logData := map[string]interface{}{
		"timestamp": time.Now().UTC().Format(time.RFC3339),
		"level":     "ERROR",
		"message":   message,
		"service":   "praxis",
		"error":     err.Error(),
	}
	
	for k, v := range details {
		logData[k] = v
	}
	
	logEntry, _ := json.Marshal(logData)
	globalDebugLogger.logger.Printf("%s", logEntry)
}