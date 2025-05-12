// GEE Flow Designer JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Canvas and element references
    const canvas = document.getElementById('flow-canvas');
    const connectionsContainer = document.getElementById('connections-container');
    const noSelection = document.getElementById('no-selection');
    const componentProperties = document.getElementById('component-properties');
    const saveBtn = document.getElementById('saveBtn');
    const saveModal = document.getElementById('save-modal');
    const cancelSaveBtn = document.getElementById('cancel-save');
    const confirmSaveBtn = document.getElementById('confirm-save');
    const validateBtn = document.getElementById('validateBtn');
    const importBtn = document.getElementById('importBtn');
    const exportBtn = document.getElementById('exportBtn');
    
    // Flow designer state
    let nodes = [];
    let connections = [];
    let nextNodeId = 1;
    let selectedNode = null;
    let isDragging = false;
    let dragOffsetX = 0;
    let dragOffsetY = 0;
    let isCreatingConnection = false;
    let connectionStartNode = null;
    let currentFlow = {
        id: null,
        name: '',
        description: '',
        version: 1
    };
    
    // Initialize SVG container size
    updateSvgContainerSize();
    
    // Event listeners for draggable components
    const draggableComponents = document.querySelectorAll('.draggable-component');
    draggableComponents.forEach(component => {
        component.addEventListener('dragstart', handleDragStart);
    });
    
    // Canvas event listeners
    canvas.addEventListener('dragover', handleDragOver);
    canvas.addEventListener('drop', handleDrop);
    canvas.addEventListener('mousedown', handleCanvasMouseDown);
    canvas.addEventListener('mousemove', handleCanvasMouseMove);
    canvas.addEventListener('mouseup', handleCanvasMouseUp);
    window.addEventListener('resize', updateSvgContainerSize);
    
    // Button event listeners
    saveBtn.addEventListener('click', openSaveModal);
    cancelSaveBtn.addEventListener('click', closeSaveModal);
    confirmSaveBtn.addEventListener('click', saveFlow);
    validateBtn.addEventListener('click', validateFlow);
    importBtn.addEventListener('click', importFlow);
    exportBtn.addEventListener('click', exportFlow);
    
    // Apply properties button event listener
    document.getElementById('apply-properties').addEventListener('click', applyProperties);
    
    // Initialize the modal 
    const saveModalElement = document.getElementById('save-modal');
    if (typeof bootstrap !== 'undefined') {
        // If Bootstrap JS is loaded, initialize the modal
        const saveModalInstance = new bootstrap.Modal(saveModalElement);
    }
    
    // Search components functionality
    const searchInput = document.getElementById('search-components');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const components = document.querySelectorAll('.draggable-component');
            
            components.forEach(component => {
                const text = component.textContent.trim().toLowerCase();
                if (text.includes(searchTerm)) {
                    component.style.display = 'block';
                } else {
                    component.style.display = 'none';
                }
            });
        });
    }
    
    // Draggable component handlers
    function handleDragStart(e) {
        const componentType = e.target.getAttribute('data-component-type');
        const componentId = e.target.getAttribute('data-component-id');
        const componentName = e.target.textContent.trim();
        
        e.dataTransfer.setData('text/plain', JSON.stringify({
            type: componentType,
            referenceId: componentId,
            name: componentName
        }));
    }
    
    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    }
    
    function handleDrop(e) {
        e.preventDefault();
        
        const data = JSON.parse(e.dataTransfer.getData('text/plain'));
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        addNode(data.type, data.referenceId, data.name, x, y);
    }
    
    // Canvas mouse event handlers
    function handleCanvasMouseDown(e) {
        const target = e.target;
        
        // Check if clicking on a node
        if (target.classList.contains('component-node') || target.closest('.component-node')) {
            const nodeElement = target.classList.contains('component-node') ? target : target.closest('.component-node');
            const nodeId = parseInt(nodeElement.getAttribute('data-node-id'));
            const node = nodes.find(n => n.id === nodeId);
            
            if (e.shiftKey) {
                // Start creating a connection
                isCreatingConnection = true;
                connectionStartNode = node;
            } else {
                // Start dragging the node
                isDragging = true;
                selectedNode = node;
                selectNode(node);
                
                const rect = nodeElement.getBoundingClientRect();
                dragOffsetX = e.clientX - rect.left;
                dragOffsetY = e.clientY - rect.top;
            }
        } else {
            // Clicked on empty canvas, deselect current node
            deselectNode();
        }
    }
    
    function handleCanvasMouseMove(e) {
        if (isDragging && selectedNode) {
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left - dragOffsetX;
            const y = e.clientY - rect.top - dragOffsetY;
            
            // Update node position
            selectedNode.x = x;
            selectedNode.y = y;
            
            // Update node element position
            const nodeElement = document.querySelector(`.component-node[data-node-id="${selectedNode.id}"]`);
            nodeElement.style.left = `${x}px`;
            nodeElement.style.top = `${y}px`;
            
            // Update connections
            updateConnections();
        } else if (isCreatingConnection && connectionStartNode) {
            // Draw temporary connection line
            const rect = canvas.getBoundingClientRect();
            const startX = connectionStartNode.x + (connectionStartNode.width / 2);
            const startY = connectionStartNode.y + (connectionStartNode.height / 2);
            const endX = e.clientX - rect.left;
            const endY = e.clientY - rect.top;
            
            // Remove previous temporary line if exists
            const tempLine = document.getElementById('temp-connection-line');
            if (tempLine) {
                tempLine.remove();
            }
            
            // Create new temporary line
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            line.setAttribute('id', 'temp-connection-line');
            line.setAttribute('d', `M ${startX} ${startY} C ${startX+50} ${startY}, ${endX-50} ${endY}, ${endX} ${endY}`);
            line.setAttribute('class', 'connector-line');
            line.setAttribute('marker-end', 'url(#arrowhead)');
            connectionsContainer.appendChild(line);
        }
    }
    
    function handleCanvasMouseUp(e) {
        if (isCreatingConnection && connectionStartNode) {
            const target = e.target;
            
            // Check if releasing on another node
            if ((target.classList.contains('component-node') || target.closest('.component-node')) && 
                !target.classList.contains('temp-connection-line')) {
                
                const nodeElement = target.classList.contains('component-node') ? target : target.closest('.component-node');
                const targetNodeId = parseInt(nodeElement.getAttribute('data-node-id'));
                const targetNode = nodes.find(n => n.id === targetNodeId);
                
                // Create connection if target node is not the same as start node
                if (targetNode && targetNode.id !== connectionStartNode.id) {
                    addConnection(connectionStartNode.id, targetNode.id, 'DEFAULT');
                }
            }
            
            // Remove temporary line
            const tempLine = document.getElementById('temp-connection-line');
            if (tempLine) {
                tempLine.remove();
            }
            
            isCreatingConnection = false;
            connectionStartNode = null;
        }
        
        isDragging = false;
    }
    
    // Node management functions
    function addNode(type, referenceId, name, x, y) {
        const nodeId = nextNodeId++;
        let width, height;
        
        switch (type) {
            case 'rule':
                width = 150;
                height = 40;
                break;
            case 'rule-group':
                width = 200;
                height = 100;
                break;
            case 'station':
                width = 240;
                height = 120;
                break;
            default:
                width = 150;
                height = 60;
        }
        
        const node = {
            id: nodeId,
            type: type,
            referenceId: referenceId,
            name: name,
            x: x,
            y: y,
            width: width,
            height: height,
            settings: {}
        };
        
        nodes.push(node);
        renderNode(node);
        selectNode(node);
        
        return node;
    }
    
    function renderNode(node) {
        const nodeElement = document.createElement('div');
        nodeElement.classList.add('component-node');
        nodeElement.setAttribute('data-node-id', node.id);
        nodeElement.style.left = `${node.x}px`;
        nodeElement.style.top = `${node.y}px`;
        
        // Create different node types
        switch (node.type) {
            case 'rule':
                nodeElement.classList.add('rule-node');
                nodeElement.style.width = `${node.width}px`;
                nodeElement.innerHTML = `<div>${node.name}</div>`;
                break;
                
            case 'rule-group':
                nodeElement.classList.add('rule-group-node');
                nodeElement.style.width = `${node.width}px`;
                nodeElement.innerHTML = `
                    <div class="rule-group-header">${node.name}</div>
                    <div class="rule-group-content"></div>
                `;
                break;
                
            case 'station':
                nodeElement.classList.add('station-node');
                nodeElement.style.width = `${node.width}px`;
                nodeElement.innerHTML = `
                    <div class="station-header">${node.name}</div>
                    <div class="station-content"></div>
                `;
                break;
        }
        
        canvas.appendChild(nodeElement);
        
        // Update node dimensions based on rendered element
        node.width = nodeElement.offsetWidth;
        node.height = nodeElement.offsetHeight;
    }
    
    function selectNode(node) {
        // Deselect current selection
        deselectNode();
        
        // Select new node
        selectedNode = node;
        const nodeElement = document.querySelector(`.component-node[data-node-id="${node.id}"]`);
        nodeElement.classList.add('selected-node');
        
        // Update properties panel
        noSelection.style.display = 'none';
        componentProperties.style.display = 'block';
        
        document.getElementById('property-title').textContent = `${node.type.charAt(0).toUpperCase() + node.type.slice(1)} Properties`;
        document.getElementById('property-name').value = node.name;
        document.getElementById('property-type').value = node.settings.type || 'action';
        document.getElementById('property-description').value = node.settings.description || '';
    }
    
    function deselectNode() {
        if (selectedNode) {
            const nodeElement = document.querySelector(`.component-node[data-node-id="${selectedNode.id}"]`);
            if (nodeElement) {
                nodeElement.classList.remove('selected-node');
            }
            selectedNode = null;
        }
        
        // Update properties panel
        noSelection.style.display = 'block';
        componentProperties.style.display = 'none';
    }
    
    function applyProperties() {
        if (selectedNode) {
            selectedNode.name = document.getElementById('property-name').value;
            selectedNode.settings.type = document.getElementById('property-type').value;
            selectedNode.settings.description = document.getElementById('property-description').value;
            
            // Update node element
            const nodeElement = document.querySelector(`.component-node[data-node-id="${selectedNode.id}"]`);
            
            switch (selectedNode.type) {
                case 'rule':
                    nodeElement.innerHTML = `<div>${selectedNode.name}</div>`;
                    break;
                    
                case 'rule-group':
                    nodeElement.querySelector('.rule-group-header').textContent = selectedNode.name;
                    break;
                    
                case 'station':
                    nodeElement.querySelector('.station-header').textContent = selectedNode.name;
                    break;
            }
            
            showToast('Success', 'Properties applied successfully');
        }
    }
    
    // Connection management functions
    function addConnection(sourceId, targetId, type) {
        const connection = {
            id: connections.length + 1,
            sourceId: sourceId,
            targetId: targetId,
            type: type,
            label: '',
            condition: '',
            style: {}
        };
        
        connections.push(connection);
        renderConnection(connection);
        
        return connection;
    }
    
    function renderConnection(connection) {
        const sourceNode = nodes.find(n => n.id === connection.sourceId);
        const targetNode = nodes.find(n => n.id === connection.targetId);
        
        if (sourceNode && targetNode) {
            const startX = sourceNode.x + (sourceNode.width / 2);
            const startY = sourceNode.y + (sourceNode.height / 2);
            const endX = targetNode.x + (targetNode.width / 2);
            const endY = targetNode.y + (targetNode.height / 2);
            
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('id', `connection-${connection.id}`);
            path.setAttribute('data-source-id', connection.sourceId);
            path.setAttribute('data-target-id', connection.targetId);
            path.setAttribute('d', `M ${startX} ${startY} C ${startX+50} ${startY}, ${endX-50} ${endY}, ${endX} ${endY}`);
            path.setAttribute('class', 'connector-line');
            path.setAttribute('marker-end', 'url(#arrowhead)');
            
            // Set styles based on connection type
            if (connection.type === 'SUCCESS') {
                path.setAttribute('stroke', '#2ecc71');
            } else if (connection.type === 'FAILURE') {
                path.setAttribute('stroke', '#e74c3c');
            } else if (connection.type === 'CONDITIONAL') {
                path.setAttribute('stroke', '#f39c12');
            }
            
            connectionsContainer.appendChild(path);
        }
    }
    
    function updateConnections() {
        connections.forEach(connection => {
            const sourceNode = nodes.find(n => n.id === connection.sourceId);
            const targetNode = nodes.find(n => n.id === connection.targetId);
            
            if (sourceNode && targetNode) {
                const startX = sourceNode.x + (sourceNode.width / 2);
                const startY = sourceNode.y + (sourceNode.height / 2);
                const endX = targetNode.x + (targetNode.width / 2);
                const endY = targetNode.y + (targetNode.height / 2);
                
                const path = document.getElementById(`connection-${connection.id}`);
                if (path) {
                    path.setAttribute('d', `M ${startX} ${startY} C ${startX+50} ${startY}, ${endX-50} ${endY}, ${endX} ${endY}`);
                }
            }
        });
    }
    
    // Flow management functions
    function openSaveModal() {
        document.getElementById('flow-name').value = currentFlow.name;
        document.getElementById('flow-description').value = currentFlow.description;
        
        // Use Bootstrap modal if available
        if (typeof bootstrap !== 'undefined') {
            const modal = bootstrap.Modal.getInstance(document.getElementById('save-modal')) || 
                          new bootstrap.Modal(document.getElementById('save-modal'));
            modal.show();
        } else {
            // Fallback to manually showing the modal
            const saveModal = document.getElementById('save-modal');
            saveModal.classList.remove('hidden');
            saveModal.style.display = 'block';
            saveModal.classList.add('show');
        }
    }
    
    function closeSaveModal() {
        // Use Bootstrap modal if available
        if (typeof bootstrap !== 'undefined') {
            const modal = bootstrap.Modal.getInstance(document.getElementById('save-modal'));
            if (modal) {
                modal.hide();
            }
        } else {
            // Fallback to manually hiding the modal
            const saveModal = document.getElementById('save-modal');
            saveModal.classList.add('hidden');
            saveModal.style.display = 'none';
            saveModal.classList.remove('show');
        }
    }
    
    function saveFlow() {
        const flowName = document.getElementById('flow-name').value;
        const flowDescription = document.getElementById('flow-description').value;
        
        if (!flowName) {
            alert('Flow name is required.');
            return;
        }
        
        currentFlow.name = flowName;
        currentFlow.description = flowDescription;
        
        // Prepare flow data for submission
        const flowData = {
            flowId: currentFlow.id,
            flowName: currentFlow.name,
            description: currentFlow.description,
            version: currentFlow.version,
            user: 'admin', // Should be replaced with actual user
            comments: 'Flow saved from designer',
            flowData: {
                nodes: nodes,
                connections: connections
            },
            nodes: nodes,
            connections: connections
        };
        
        // Submit flow data to the server
        fetch('/save_flow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(flowData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentFlow.id = data.flowId;
                showToast('Success', data.message);
                closeSaveModal();
            } else {
                showToast('Error', data.message, 'error');
            }
        })
        .catch(error => {
            showToast('Error', 'Failed to save flow: ' + error, 'error');
        });
    }
    
    function validateFlow() {
        // Simple validation - check if there are any nodes
        if (nodes.length === 0) {
            showToast('Warning', 'Flow has no nodes. Please add nodes to your flow.', 'warning');
            return;
        }
        
        // Check if all nodes are connected
        const connectedNodeIds = new Set();
        connections.forEach(conn => {
            connectedNodeIds.add(conn.sourceId);
            connectedNodeIds.add(conn.targetId);
        });
        
        if (connectedNodeIds.size < nodes.length) {
            showToast('Warning', 'Some nodes are not connected. Please connect all nodes.', 'warning');
            return;
        }
        
        showToast('Success', 'Flow validation passed');
    }
    
    function importFlow() {
        // Create input element for file selection
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.json';
        
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                
                reader.onload = function(event) {
                    try {
                        const flowData = JSON.parse(event.target.result);
                        
                        // Reset current flow designer
                        nodes = [];
                        connections = [];
                        nextNodeId = 1;
                        
                        // Clear canvas
                        const canvasNodes = document.querySelectorAll('.component-node');
                        canvasNodes.forEach(node => node.remove());
                        
                        // Clear connections
                        while (connectionsContainer.lastChild) {
                            if (connectionsContainer.lastChild.tagName !== 'defs') {
                                connectionsContainer.removeChild(connectionsContainer.lastChild);
                            }
                        }
                        
                        // Set current flow data
                        if (flowData.flow) {
                            currentFlow = {
                                id: flowData.flow.id,
                                name: flowData.flow.name,
                                description: flowData.flow.description,
                                version: flowData.flow.version || 1
                            };
                        }
                        
                        // Load nodes
                        if (flowData.nodes && Array.isArray(flowData.nodes)) {
                            // Find the highest ID to set nextNodeId correctly
                            let highestId = 0;
                            
                            flowData.nodes.forEach(node => {
                                const newNode = addNode(
                                    node.type, 
                                    node.referenceId, 
                                    node.name, 
                                    node.x, 
                                    node.y
                                );
                                
                                // Copy additional settings
                                if (node.settings) {
                                    newNode.settings = JSON.parse(JSON.stringify(node.settings));
                                }
                                
                                if (node.id > highestId) {
                                    highestId = node.id;
                                }
                            });
                            
                            nextNodeId = highestId + 1;
                        }
                        
                        // Load connections
                        if (flowData.connections && Array.isArray(flowData.connections)) {
                            flowData.connections.forEach(conn => {
                                addConnection(conn.sourceId, conn.targetId, conn.type);
                            });
                        }
                        
                        showToast('Success', 'Flow imported successfully');
                    } catch (error) {
                        showToast('Error', 'Failed to import flow: ' + error, 'error');
                    }
                };
                
                reader.readAsText(file);
            }
        });
        
        fileInput.click();
    }
    
    function exportFlow() {
        // Check if we have any nodes
        if (nodes.length === 0) {
            showToast('Warning', 'No flow to export. Please create a flow first.', 'warning');
            return;
        }
        
        // Create flow data JSON
        const flowData = {
            flow: {
                id: currentFlow.id,
                name: currentFlow.name,
                description: currentFlow.description,
                version: currentFlow.version
            },
            nodes: nodes,
            connections: connections
        };
        
        // Create download link
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(flowData, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", `${currentFlow.name || 'flow'}.json`);
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
        
        showToast('Success', 'Flow exported successfully');
    }
    
    // Utility functions
    function updateSvgContainerSize() {
        const svg = document.getElementById('connections-container');
        svg.setAttribute('width', canvas.offsetWidth);
        svg.setAttribute('height', canvas.offsetHeight);
    }
    
    function showToast(title, message, type = 'success') {
        // Check if we have the showToast function from base.html
        if (typeof window.showToast === 'function') {
            window.showToast(title, message, type);
            return;
        }
        
        // Fallback toast implementation
        const toast = document.createElement('div');
        toast.className = `toast position-fixed top-0 end-0 m-3 bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'warning'} text-white`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Use Bootstrap toast if available
        if (typeof bootstrap !== 'undefined') {
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
        } else {
            // Simple fallback
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
                document.body.removeChild(toast);
            }, 3000);
        }
    }
    
    // Load flow data if ID is in URL
    function loadFlowFromId() {
        const urlParams = new URLSearchParams(window.location.search);
        const flowId = urlParams.get('flow_id');
        
        if (flowId) {
            fetch(`/get_flow/${flowId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.flow) {
                        // Clear existing canvas
                        const canvasNodes = document.querySelectorAll('.component-node');
                        canvasNodes.forEach(node => node.remove());
                        
                        // Clear connections
                        while (connectionsContainer.lastChild) {
                            if (connectionsContainer.lastChild.tagName !== 'defs') {
                                connectionsContainer.removeChild(connectionsContainer.lastChild);
                            }
                        }
                        
                        // Set current flow data
                        currentFlow = {
                            id: data.flow.FLOW_ID,
                            name: data.flow.FLOW_NAME,
                            description: data.flow.DESCRIPTION,
                            version: data.flow.VERSION
                        };
                        
                        // Load nodes
                        if (data.nodes && Array.isArray(data.nodes)) {
                            // Map database IDs to local IDs
                            const idMap = {};
                            let highestId = 0;
                            
                            data.nodes.forEach(node => {
                                const settings = node.CUSTOM_SETTINGS ? JSON.parse(node.CUSTOM_SETTINGS) : {};
                                
                                const newNode = addNode(
                                    node.NODE_TYPE,
                                    node.REFERENCE_ID,
                                    node.LABEL || 'Unnamed',
                                    node.POSITION_X,
                                    node.POSITION_Y
                                );
                                
                                // Store mapping from DB ID to local ID
                                idMap[node.NODE_ID] = newNode.id;
                                
                                // Copy settings
                                newNode.settings = settings;
                                
                                if (newNode.id > highestId) {
                                    highestId = newNode.id;
                                }
                            });
                            
                            nextNodeId = highestId + 1;
                            
                            // Load connections
                            if (data.connections && Array.isArray(data.connections)) {
                                data.connections.forEach(conn => {
                                    // Map DB IDs to local IDs
                                    const sourceId = idMap[conn.SOURCE_NODE_ID];
                                    const targetId = idMap[conn.TARGET_NODE_ID];
                                    
                                    if (sourceId && targetId) {
                                        addConnection(sourceId, targetId, conn.CONNECTION_TYPE || 'DEFAULT');
                                    }
                                });
                            }
                            
                            showToast('Success', 'Flow loaded successfully');
                        }
                    }
                })
                .catch(error => {
                    showToast('Error', 'Failed to load flow: ' + error, 'error');
                });
        }
    }
    
    // Call this function on load
    loadFlowFromId();
});