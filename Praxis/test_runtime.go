package main

import (
    "fmt" 
    "github.com/GEE/Praxis/internal/runtime"
)

func main() {
    loader, err := runtime.NewRuntimeLoader("../Forge/praxis_runtime.db")
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    defer loader.Close()
    
    flows, err := loader.LoadActiveFlows()
    if err != nil {
        fmt.Printf("Error loading flows: %v\n", err)
        return
    }
    
    fmt.Printf("Loaded %d flows\n", len(flows))
    for _, flow := range flows {
        fmt.Printf("- Flow ID: %d, Name: %s\n", flow.ID, flow.Name)
    }
}