// GEE Flow Designer JavaScript - Enhanced Version with SVG Animations
// Version: 3.0 - Complete implementation with edge connections and directional arrows

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
    const loadBtn = document.getElementById('loadBtn');
    const animateAllBtn = document.getElementById('animateAllBtn');
    const stopAnimationBtn = document.getElementById('stopAnimationBtn');
    const importBtn = document.getElementById('importBtn');
    const exportBtn = document.getElementById('exportBtn');
    
    // Palette containers
    const ruleGroupsPalette = document.getElementById('rule-groups-palette');
    
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
    
    // Component data
    let allRuleGroups = [];
    
    // Initialize the flow designer
    initializeFlowDesigner();
    
    function initializeFlowDesigner() {
        console.log('Initializing Flow Designer...');
        
        // Initialize SVG container size
        updateSvgContainerSize();
        
        // Load component palette data
        loadPaletteData();
        
        // Setup event listeners
        setupEventListeners();
        
        // Load flow if ID is in URL
        loadFlowFromId();
        
        // Add debug function for testing arrows
        window.testArrows = function() {
            const svg = connectionsContainer;
            const testPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            testPath.setAttribute('d', 'M 100 100 L 300 100');
            testPath.setAttribute('stroke', '#ff0000');
            testPath.setAttribute('stroke-width', '3');
            testPath.setAttribute('marker-end', 'url(#arrowhead-failure)');
            testPath.setAttribute('fill', 'none');
            svg.appendChild(testPath);
            console.log('Test arrow added');
        };
    }
    
    function loadPaletteData() {
        // Load rule groups
        fetch('/flow_designer/get_palette_rule_groups')
            .then(response => response.json())
            .then(data => {
                allRuleGroups = data;
                renderRuleGroupsPalette(data);
            })
            .catch(error => {
                console.error('Error loading rule groups:', error);
                showToast('Error', 'Failed to load rule groups', 'error');
            });
    }
    
    
    function renderRuleGroupsPalette(ruleGroups) {
        if (!ruleGroupsPalette) return;
        
        if (ruleGroups.length === 0) {
            ruleGroupsPalette.innerHTML = '<div class="text-center py-2 text-muted">No rule groups available</div>';
            return;
        }
        
        ruleGroupsPalette.innerHTML = '';
        ruleGroups.forEach(group => {
            const groupElement = document.createElement('div');
            groupElement.classList.add('draggable-component', 'rule-group-item');
            groupElement.draggable = true;
            groupElement.innerHTML = `
                <div class="p-2 border rounded mb-2 bg-success bg-opacity-10">
                    <div class="fw-bold text-success">${group.name}</div>
                    <small class="text-muted">Rule Group</small>
                </div>
            `;
            
            groupElement.addEventListener('dragstart', handleDragStart);
            groupElement.setAttribute('data-type', 'rule-group');
            groupElement.setAttribute('data-reference-id', group.id);
            groupElement.setAttribute('data-name', group.name);
            
            ruleGroupsPalette.appendChild(groupElement);
        });
    }
    
    
    function setupEventListeners() {
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
        loadBtn.addEventListener('click', openLoadModal);
        animateAllBtn.addEventListener('click', animateAllConnections);
        stopAnimationBtn.addEventListener('click', stopAllAnimations);
        importBtn.addEventListener('click', importFlow);
        exportBtn.addEventListener('click', exportFlow);
        
        // Apply properties button event listener
        document.getElementById('apply-properties').addEventListener('click', applyProperties);
        
        // Search components functionality
        const searchInput = document.getElementById('search-components');
        if (searchInput) {
            searchInput.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                filterComponents(searchTerm);
            });
        }
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', handleKeyboardShortcuts);
    }
    
    function handleKeyboardShortcuts(e) {
        // Delete selected node with Delete key
        if (e.key === 'Delete' && selectedNode) {
            deleteSelectedNode();
        }
        
        // Save flow with Ctrl+S
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            openSaveModal();
        }
        
        // Escape to deselect
        if (e.key === 'Escape') {
            deselectNode();
        }
        
        // Animate all connections with A key
        if (e.key === 'a' || e.key === 'A') {
            e.preventDefault();
            animateAllConnections();
        }
        
        // Stop animations with X key
        if (e.key === 'x' || e.key === 'X') {
            e.preventDefault();
            stopAllAnimations();
        }
    }
    
    function filterComponents(searchTerm) {
        const allComponents = document.querySelectorAll('.draggable-component');
        
        allComponents.forEach(component => {
            const text = component.textContent.trim().toLowerCase();
            if (text.includes(searchTerm)) {
                component.style.display = 'block';
            } else {
                component.style.display = 'none';
            }
        });
    }
    
    function handleDragStart(e) {
        const componentData = {
            type: e.currentTarget.getAttribute('data-type'),
            referenceId: e.currentTarget.getAttribute('data-reference-id'),
            name: e.currentTarget.getAttribute('data-name')
        };
        
        e.dataTransfer.setData('text/plain', JSON.stringify(componentData));
        e.dataTransfer.effectAllowed = 'copy';
    }
    
    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    }
    
    function handleDrop(e) {
        e.preventDefault();
        
        try {
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            addNode(data.type, data.referenceId, data.name, x, y);
        } catch (error) {
            console.error('Error handling drop:', error);
        }
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
                // Start creating a connection with Shift+Click
                isCreatingConnection = true;
                connectionStartNode = node;
                e.preventDefault();
                console.log('Connection creation started from node:', node.id);
                showToast('Info', `Connection started from "${node.name}". Click target node to complete.`, 'info');
            } else {
                // Start dragging the node
                isDragging = true;
                selectedNode = node;
                selectNode(node);
                
                const rect = nodeElement.getBoundingClientRect();
                const canvasRect = canvas.getBoundingClientRect();
                dragOffsetX = e.clientX - canvasRect.left - node.x;
                dragOffsetY = e.clientY - canvasRect.top - node.y;
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
            selectedNode.x = Math.max(0, Math.min(x, canvas.clientWidth - selectedNode.width));
            selectedNode.y = Math.max(0, Math.min(y, canvas.clientHeight - selectedNode.height));
            
            // Update DOM element
            const nodeElement = document.querySelector(`[data-node-id="${selectedNode.id}"]`);
            if (nodeElement) {
                nodeElement.style.left = `${selectedNode.x}px`;
                nodeElement.style.top = `${selectedNode.y}px`;
            }
            
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
            line.setAttribute('d', createBezierPath(startX, startY, endX, endY));
            line.setAttribute('class', 'connector-line');
            line.setAttribute('marker-end', 'url(#arrowhead)');
            line.setAttribute('stroke-dasharray', '5,5');
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
                    console.log('Connection completed between nodes:', connectionStartNode.id, '->', targetNode.id);
                    console.log('Event coordinates:', e.clientX, e.clientY);
                    showConnectionTypeSelector(connectionStartNode.id, targetNode.id, e);
                } else {
                    console.log('Invalid connection attempt');
                    showToast('Warning', 'Cannot connect to the same node', 'warning');
                }
            }
            
            // Remove temporary line
            const tempLine = document.getElementById('temp-connection-line');
            if (tempLine) {
                tempLine.remove();
            }
            
            // Reset connection creation state
            isCreatingConnection = false;
            connectionStartNode = null;
        }
        
        // Stop dragging
        isDragging = false;
    }
    
    function addNode(type, referenceId, name, x, y) {
        const node = {
            id: nextNodeId++,
            type: type,
            referenceId: referenceId,
            name: name,
            x: x - 75, // Center the node on cursor
            y: y - 30,
            width: 150,
            height: 60,
            settings: {}
        };
        
        nodes.push(node);
        renderNode(node);
        
        showToast('Success', `Added ${type}: ${name}`);
        
        return node;
    }
    
    function renderNode(node) {
        const nodeElement = document.createElement('div');
        nodeElement.classList.add('component-node');
        nodeElement.setAttribute('data-node-id', node.id);
        nodeElement.style.left = `${node.x}px`;
        nodeElement.style.top = `${node.y}px`;
        nodeElement.style.position = 'absolute';
        nodeElement.style.userSelect = 'none';
        nodeElement.style.cursor = 'move';
        
        // Create rule group nodes
        if (node.type === 'rule-group') {
            nodeElement.classList.add('rule-group-node');
            nodeElement.style.width = `${node.width}px`;
            nodeElement.innerHTML = `
                <div class="rule-group-header">${node.name}</div>
                <div class="rule-group-content">
                    <small>Rule Group</small>
                </div>
            `;
        }
        
        canvas.appendChild(nodeElement);
        
        // Add right-click context menu for easier connection creation
        nodeElement.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            showNodeContextMenu(node, e);
        });
        
        // Update node dimensions based on rendered element
        node.width = nodeElement.offsetWidth;
        node.height = nodeElement.offsetHeight;
    }
    
    function selectNode(node) {
        // Deselect current selection
        deselectNode();
        
        // Select new node
        selectedNode = node;
        const nodeElement = document.querySelector(`[data-node-id="${node.id}"]`);
        if (nodeElement) {
            nodeElement.classList.add('selected-node');
        }
        
        // Update properties panel
        showNodeProperties(node);
    }
    
    function deselectNode() {
        if (selectedNode) {
            const nodeElement = document.querySelector(`[data-node-id="${selectedNode.id}"]`);
            if (nodeElement) {
                nodeElement.classList.remove('selected-node');
            }
            selectedNode = null;
        }
        
        // Hide properties panel
        hideNodeProperties();
    }
    
    function showNodeProperties(node) {
        noSelection.style.display = 'none';
        componentProperties.style.display = 'block';
        
        document.getElementById('property-title').textContent = `${node.type.charAt(0).toUpperCase() + node.type.slice(1)} Properties`;
        document.getElementById('property-name').value = node.name;
        document.getElementById('property-type').value = node.type;
    }
    
    function hideNodeProperties() {
        noSelection.style.display = 'block';
        componentProperties.style.display = 'none';
    }
    
    function applyProperties() {
        if (selectedNode) {
            const newName = document.getElementById('property-name').value.trim();
            if (newName) {
                selectedNode.name = newName;
                
                // Update the visual representation
                const nodeElement = document.querySelector(`[data-node-id="${selectedNode.id}"]`);
                if (nodeElement) {
                    if (selectedNode.type === 'rule-group') {
                        nodeElement.querySelector('.rule-group-header').textContent = selectedNode.name;
                    }
                }
            }
            
            showToast('Success', 'Properties applied successfully');
        }
    }
    
    // Connection management functions
    function showConnectionTypeSelector(sourceId, targetId, event) {
        // Remove any existing menu first
        closeConnectionTypeMenu();
        
        // Create a floating menu for connection type selection
        const menu = document.createElement('div');
        menu.id = 'connection-type-menu';
        menu.className = 'position-fixed bg-white border rounded shadow p-3';
        
        // Better positioning - offset from cursor to avoid conflicts
        const x = Math.min(event.clientX + 10, window.innerWidth - 220);
        const y = Math.min(event.clientY + 10, window.innerHeight - 300);
        
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
        menu.style.zIndex = '99999';
        menu.style.minWidth = '200px';
        menu.style.border = '2px solid #007bff';
        menu.style.backgroundColor = 'white';
        menu.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
        
        menu.innerHTML = `
            <div class="mb-3 text-center"><strong style="color: #007bff;">🔗 Select Connection Type</strong></div>
            <button class="btn btn-sm btn-outline-secondary w-100 mb-2" onclick="createConnectionWithType(${sourceId}, ${targetId}, 'DEFAULT')" style="border: 1px solid #666;">
                <i class="fas fa-arrow-right"></i> Default Flow
            </button>
            <button class="btn btn-sm btn-outline-success w-100 mb-2" onclick="createConnectionWithType(${sourceId}, ${targetId}, 'SUCCESS')" style="border: 1px solid #28a745;">
                <i class="fas fa-check"></i> Success Path
            </button>
            <button class="btn btn-sm btn-outline-danger w-100 mb-2" onclick="createConnectionWithType(${sourceId}, ${targetId}, 'FAILURE')" style="border: 1px solid #dc3545;">
                <i class="fas fa-times"></i> Failure Path
            </button>
            <button class="btn btn-sm btn-outline-warning w-100 mb-2" onclick="createConnectionWithType(${sourceId}, ${targetId}, 'CONDITIONAL')" style="border: 1px solid #ffc107;">
                <i class="fas fa-question"></i> Conditional
            </button>
            <hr class="my-2">
            <button class="btn btn-sm btn-secondary w-100" onclick="closeConnectionTypeMenu()" style="background-color: #6c757d;">
                <i class="fas fa-times"></i> Cancel
            </button>
        `;
        
        document.body.appendChild(menu);
        console.log('Connection type menu created at:', x, y);
        console.log('Menu element:', menu);
        
        // Add fallback - if menu doesn't appear, create default connection after 3 seconds
        setTimeout(() => {
            const stillExists = document.getElementById('connection-type-menu');
            if (!stillExists) {
                console.log('Menu disappeared, creating default connection');
                createConnectionWithType(sourceId, targetId, 'DEFAULT');
            }
        }, 3000);
        
        // Show a toast to guide the user
        showToast('Info', 'Select connection type from the popup menu', 'info');
        
        // Close menu when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function closeMenuHandler(e) {
                if (!menu.contains(e.target)) {
                    closeConnectionTypeMenu();
                    document.removeEventListener('click', closeMenuHandler);
                }
            });
        }, 100);
    }
    
    function createConnectionWithType(sourceId, targetId, type) {
        closeConnectionTypeMenu();
        addConnection(sourceId, targetId, type);
    }
    
    function closeConnectionTypeMenu() {
        const menu = document.getElementById('connection-type-menu');
        if (menu) {
            menu.remove();
        }
    }
    
    function showNodeContextMenu(node, event) {
        // Remove any existing menus
        closeNodeContextMenu();
        closeConnectionTypeMenu();
        
        const menu = document.createElement('div');
        menu.id = 'node-context-menu';
        menu.className = 'position-fixed bg-white border rounded shadow p-3';
        
        const x = Math.min(event.clientX + 10, window.innerWidth - 250);
        const y = Math.min(event.clientY + 10, window.innerHeight - 200);
        
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
        menu.style.zIndex = '99999';
        menu.style.minWidth = '200px';
        menu.style.border = '2px solid #28a745';
        menu.style.backgroundColor = 'white';
        menu.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
        
        // Get other nodes for connection options
        const otherNodes = nodes.filter(n => n.id !== node.id);
        
        let connectionOptions = '';
        if (otherNodes.length > 0) {
            connectionOptions = '<div class="mb-2"><strong>🔗 Connect To:</strong></div>';
            otherNodes.slice(0, 5).forEach(targetNode => {
                connectionOptions += `
                    <button class="btn btn-sm btn-outline-primary w-100 mb-1" onclick="quickConnect(${node.id}, ${targetNode.id})">
                        → ${targetNode.name}
                    </button>
                `;
            });
            if (otherNodes.length > 5) {
                connectionOptions += '<small class="text-muted d-block mb-2">And ' + (otherNodes.length - 5) + ' more...</small>';
            }
        } else {
            connectionOptions = '<small class="text-muted">No other nodes to connect to</small>';
        }
        
        menu.innerHTML = `
            <div class="mb-2 text-center"><strong style="color: #28a745;">📋 ${node.name}</strong></div>
            <hr class="my-2">
            ${connectionOptions}
            <hr class="my-2">
            <button class="btn btn-sm btn-outline-danger w-100 mb-1" onclick="deleteNodeById(${node.id})">
                <i class="fas fa-trash"></i> Delete Node
            </button>
            <button class="btn btn-sm btn-secondary w-100" onclick="closeNodeContextMenu()">
                <i class="fas fa-times"></i> Close
            </button>
        `;
        
        document.body.appendChild(menu);
        
        // Close menu when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function closeMenuHandler(e) {
                if (!menu.contains(e.target)) {
                    closeNodeContextMenu();
                    document.removeEventListener('click', closeMenuHandler);
                }
            });
        }, 100);
    }
    
    function closeNodeContextMenu() {
        const menu = document.getElementById('node-context-menu');
        if (menu) {
            menu.remove();
        }
    }
    
    function quickConnect(sourceId, targetId) {
        closeNodeContextMenu();
        showConnectionTypeSelector(sourceId, targetId, { 
            clientX: window.innerWidth / 2, 
            clientY: window.innerHeight / 2 
        });
    }
    
    function deleteNodeById(nodeId) {
        if (confirm('Are you sure you want to delete this node and all its connections?')) {
            closeNodeContextMenu();
            
            // Remove connections involving this node
            connections = connections.filter(conn => {
                if (conn.sourceId === nodeId || conn.targetId === nodeId) {
                    const connectionElement = document.getElementById(`connection-${conn.id}`);
                    if (connectionElement) {
                        connectionElement.remove();
                    }
                    return false;
                }
                return true;
            });
            
            // Remove the node
            nodes = nodes.filter(node => node.id !== nodeId);
            
            // Remove DOM element
            const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
            if (nodeElement) {
                nodeElement.remove();
            }
            
            // Deselect if this was the selected node
            if (selectedNode && selectedNode.id === nodeId) {
                deselectNode();
            }
            
            showToast('Success', 'Node deleted successfully');
        }
    }
    
    function addConnection(sourceId, targetId, type) {
        // Check if connection already exists
        const existingConnection = connections.find(conn => 
            conn.sourceId === sourceId && conn.targetId === targetId
        );
        
        if (existingConnection) {
            showToast('Warning', 'Connection already exists between these nodes', 'warning');
            return null;
        }
        
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
        
        showToast('Success', 'Connection created successfully');
        return connection;
    }
    
    function renderConnection(connection) {
        const sourceNode = nodes.find(n => n.id === connection.sourceId);
        const targetNode = nodes.find(n => n.id === connection.targetId);
        
        if (sourceNode && targetNode) {
            // Calculate connection points at component edges
            const { startX, startY, endX, endY } = calculateConnectionPoints(sourceNode, targetNode);
            
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('id', `connection-${connection.id}`);
            path.setAttribute('data-source-id', connection.sourceId);
            path.setAttribute('data-target-id', connection.targetId);
            path.setAttribute('d', createBezierPath(startX, startY, endX, endY));
            path.setAttribute('class', 'connector-line');
            path.style.cursor = 'pointer';
            path.style.pointerEvents = 'stroke';
            path.setAttribute('fill', 'none');
            
            // Set styles and markers based on connection type
            switch (connection.type) {
                case 'SUCCESS':
                    path.setAttribute('stroke', '#2ecc71');
                    path.setAttribute('stroke-width', '3');
                    path.setAttribute('marker-end', 'url(#arrowhead-success)');
                    break;
                case 'FAILURE':
                    path.setAttribute('stroke', '#e74c3c');
                    path.setAttribute('stroke-width', '3');
                    path.setAttribute('marker-end', 'url(#arrowhead-failure)');
                    break;
                case 'CONDITIONAL':
                    path.setAttribute('stroke', '#f39c12');
                    path.setAttribute('stroke-width', '3');
                    path.setAttribute('stroke-dasharray', '8,4');
                    path.setAttribute('marker-end', 'url(#arrowhead-conditional)');
                    break;
                default:
                    path.setAttribute('stroke', '#666');
                    path.setAttribute('stroke-width', '2');
                    path.setAttribute('marker-end', 'url(#arrowhead)');
            }
            
            // Add hover effect
            path.addEventListener('mouseenter', function() {
                this.setAttribute('stroke-width', (parseInt(this.getAttribute('stroke-width')) + 1).toString());
                this.style.filter = 'drop-shadow(0 0 4px rgba(0,0,0,0.3))';
            });
            
            path.addEventListener('mouseleave', function() {
                this.setAttribute('stroke-width', (parseInt(this.getAttribute('stroke-width')) - 1).toString());
                this.style.filter = 'none';
            });
            
            // Add click event to delete connection
            path.addEventListener('click', function(e) {
                e.stopPropagation();
                if (confirm('Delete this connection?')) {
                    deleteConnection(connection.id);
                }
            });
            
            connectionsContainer.appendChild(path);
            
            // Add double-click to animate flow
            path.addEventListener('dblclick', function(e) {
                e.stopPropagation();
                animateFlow(connection.id);
            });
        }
    }
    
    function animateFlow(connectionId) {
        const connection = connections.find(conn => conn.id === connectionId);
        if (!connection) return;
        
        const sourceNode = nodes.find(n => n.id === connection.sourceId);
        const targetNode = nodes.find(n => n.id === connection.targetId);
        
        if (sourceNode && targetNode) {
            createFlowAnimation(connection, sourceNode, targetNode);
        }
    }
    
    function createFlowAnimation(connection, sourceNode, targetNode) {
        // Calculate connection points at component edges
        const { startX, startY, endX, endY } = calculateConnectionPoints(sourceNode, targetNode);
        
        // Create animated dot
        const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        dot.setAttribute('r', '4');
        dot.setAttribute('fill', getAnimationColor(connection.type));
        dot.setAttribute('opacity', '0.9');
        dot.classList.add('flow-animation-dot');
        
        // Create animation for the dot moving along the path
        const animateMotion = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
        animateMotion.setAttribute('dur', '2s');
        animateMotion.setAttribute('repeatCount', '3');
        animateMotion.setAttribute('rotate', 'auto');
        
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', createBezierPath(startX, startY, endX, endY));
        
        const mpath = document.createElementNS('http://www.w3.org/2000/svg', 'mpath');
        mpath.setAttributeNS('http://www.w3.org/1999/xlink', 'href', '#temp-animation-path');
        
        // Create temporary path for animation
        const tempPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        tempPath.setAttribute('id', 'temp-animation-path');
        tempPath.setAttribute('d', createBezierPath(startX, startY, endX, endY));
        tempPath.setAttribute('opacity', '0');
        
        connectionsContainer.appendChild(tempPath);
        
        // Use path reference for motion
        animateMotion.innerHTML = `<mpath href="#temp-animation-path"/>`;
        dot.appendChild(animateMotion);
        
        // Add pulsing animation
        const pulse = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
        pulse.setAttribute('attributeName', 'r');
        pulse.setAttribute('values', '3;6;3');
        pulse.setAttribute('dur', '0.5s');
        pulse.setAttribute('repeatCount', 'indefinite');
        dot.appendChild(pulse);
        
        connectionsContainer.appendChild(dot);
        
        // Remove animation elements after completion
        setTimeout(() => {
            if (dot.parentNode) dot.remove();
            if (tempPath.parentNode) tempPath.remove();
        }, 6500);
        
        // Show toast notification
        showToast('Info', `Flow animation started on ${connection.type.toLowerCase()} connection`, 'info');
    }
    
    function getAnimationColor(connectionType) {
        switch (connectionType) {
            case 'SUCCESS': return '#2ecc71';
            case 'FAILURE': return '#e74c3c';
            case 'CONDITIONAL': return '#f39c12';
            default: return '#007bff';
        }
    }
    
    function animateAllConnections() {
        connections.forEach((connection, index) => {
            setTimeout(() => {
                animateFlow(connection.id);
            }, index * 500); // Stagger animations
        });
        
        if (connections.length > 0) {
            showToast('Info', `Animating ${connections.length} connections`, 'info');
        } else {
            showToast('Warning', 'No connections to animate', 'warning');
        }
    }
    
    function stopAllAnimations() {
        const animationDots = document.querySelectorAll('.flow-animation-dot');
        animationDots.forEach(dot => {
            if (dot.parentNode) dot.remove();
        });
        
        const tempPaths = document.querySelectorAll('[id^="temp-animation-path"]');
        tempPaths.forEach(path => {
            if (path.parentNode) path.remove();
        });
        
        showToast('Info', 'All animations stopped', 'info');
    }
    
    function deleteConnection(connectionId) {
        // Remove from connections array
        connections = connections.filter(conn => conn.id !== connectionId);
        
        // Remove from DOM
        const connectionElement = document.getElementById(`connection-${connectionId}`);
        if (connectionElement) {
            connectionElement.remove();
        }
        
        showToast('Success', 'Connection deleted successfully');
    }
    
    function calculateConnectionPoints(sourceNode, targetNode) {
        // Calculate connection points at the edges of the components
        const sourceCenterX = sourceNode.x + (sourceNode.width / 2);
        const sourceCenterY = sourceNode.y + (sourceNode.height / 2);
        const targetCenterX = targetNode.x + (targetNode.width / 2);
        const targetCenterY = targetNode.y + (targetNode.height / 2);
        
        // Calculate direction vector
        const dx = targetCenterX - sourceCenterX;
        const dy = targetCenterY - sourceCenterY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance === 0) {
            return { startX: sourceCenterX, startY: sourceCenterY, endX: targetCenterX, endY: targetCenterY };
        }
        
        // Normalize direction
        const normalizedDx = dx / distance;
        const normalizedDy = dy / distance;
        
        // Calculate connection points at component edges
        let startX, startY, endX, endY;
        
        // Source node edge point
        if (Math.abs(normalizedDx) > Math.abs(normalizedDy)) {
            // Horizontal connection - use left/right edges
            if (normalizedDx > 0) {
                // Going right - use right edge of source
                startX = sourceNode.x + sourceNode.width;
                startY = sourceCenterY;
            } else {
                // Going left - use left edge of source
                startX = sourceNode.x;
                startY = sourceCenterY;
            }
        } else {
            // Vertical connection - use top/bottom edges
            if (normalizedDy > 0) {
                // Going down - use bottom edge of source
                startX = sourceCenterX;
                startY = sourceNode.y + sourceNode.height;
            } else {
                // Going up - use top edge of source
                startX = sourceCenterX;
                startY = sourceNode.y;
            }
        }
        
        // Target node edge point
        if (Math.abs(normalizedDx) > Math.abs(normalizedDy)) {
            // Horizontal connection - use left/right edges
            if (normalizedDx > 0) {
                // Coming from left - use left edge of target
                endX = targetNode.x;
                endY = targetCenterY;
            } else {
                // Coming from right - use right edge of target
                endX = targetNode.x + targetNode.width;
                endY = targetCenterY;
            }
        } else {
            // Vertical connection - use top/bottom edges
            if (normalizedDy > 0) {
                // Coming from top - use top edge of target
                endX = targetCenterX;
                endY = targetNode.y;
            } else {
                // Coming from bottom - use bottom edge of target
                endX = targetCenterX;
                endY = targetNode.y + targetNode.height;
            }
        }
        
        return { startX, startY, endX, endY };
    }
    
    function createBezierPath(startX, startY, endX, endY) {
        const controlOffset = Math.min(100, Math.abs(endX - startX) / 2);
        return `M ${startX} ${startY} C ${startX + controlOffset} ${startY}, ${endX - controlOffset} ${endY}, ${endX} ${endY}`;
    }
    
    function updateConnections() {
        connections.forEach(connection => {
            const sourceNode = nodes.find(n => n.id === connection.sourceId);
            const targetNode = nodes.find(n => n.id === connection.targetId);
            
            if (sourceNode && targetNode) {
                // Calculate connection points at component edges
                const { startX, startY, endX, endY } = calculateConnectionPoints(sourceNode, targetNode);
                
                const path = document.getElementById(`connection-${connection.id}`);
                if (path) {
                    path.setAttribute('d', createBezierPath(startX, startY, endX, endY));
                }
            }
        });
    }
    
    // Flow management functions
    function openSaveModal() {
        document.getElementById('flow-name').value = currentFlow.name || '';
        document.getElementById('flow-description').value = currentFlow.description || '';
        
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('save-modal'));
        modal.show();
    }
    
    function closeSaveModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('save-modal'));
        if (modal) {
            modal.hide();
        }
    }
    
    function saveFlow() {
        const flowName = document.getElementById('flow-name').value.trim();
        const flowDescription = document.getElementById('flow-description').value.trim();
        
        if (!flowName) {
            showToast('Error', 'Flow name is required', 'error');
            return;
        }
        
        if (nodes.length === 0) {
            showToast('Warning', 'Cannot save empty flow. Please add some nodes first.', 'warning');
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
            nodes: nodes,
            connections: connections
        };
        
        // Submit flow data to the server
        fetch('/flow_designer/save_flow', {
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
            showToast('Error', 'Failed to save flow: ' + error.message, 'error');
            console.error('Save error:', error);
        });
    }
    
    function openLoadModal() {
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('load-modal'));
        
        // Show loading state
        document.getElementById('flows-loading').classList.remove('d-none');
        document.getElementById('flows-list').classList.add('d-none');
        document.getElementById('no-flows').classList.add('d-none');
        
        modal.show();
        
        // Load saved flows
        loadSavedFlows();
    }
    
    function loadSavedFlows() {
        fetch('/flow_designer/get_flows')
        .then(response => response.json())
        .then(flows => {
            document.getElementById('flows-loading').classList.add('d-none');
            
            if (flows.length === 0) {
                document.getElementById('no-flows').classList.remove('d-none');
            } else {
                document.getElementById('flows-list').classList.remove('d-none');
                renderFlowsList(flows);
            }
        })
        .catch(error => {
            document.getElementById('flows-loading').classList.add('d-none');
            showToast('Error', 'Failed to load flows: ' + error.message, 'error');
            console.error('Load flows error:', error);
        });
    }
    
    function renderFlowsList(flows) {
        const container = document.getElementById('flows-container');
        container.innerHTML = '';
        
        flows.forEach(flow => {
            const flowCard = document.createElement('div');
            flowCard.className = 'col-md-6 mb-3';
            
            const lastUpdate = new Date(flow.UPDATE_DATE).toLocaleDateString();
            
            flowCard.innerHTML = `
                <div class="card h-100">
                    <div class="card-body">
                        <h6 class="card-title">${escapeHtml(flow.FLOW_NAME)}</h6>
                        <p class="card-text text-muted small">${escapeHtml(flow.DESCRIPTION || 'No description')}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">v${flow.VERSION}</small>
                            <small class="text-muted">${lastUpdate}</small>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-2">
                            <span class="badge bg-${flow.STATUS === 'ACTIVE' ? 'success' : 'secondary'}">${flow.STATUS}</span>
                            <small class="text-muted">by ${escapeHtml(flow.LAST_EDITED_BY)}</small>
                        </div>
                    </div>
                    <div class="card-footer bg-transparent">
                        <div class="d-flex gap-2">
                            <button class="btn btn-primary btn-sm flex-fill" onclick="loadSelectedFlow(${flow.FLOW_ID})">
                                <i class="fas fa-download"></i> Load
                            </button>
                            <button class="btn btn-outline-danger btn-sm" onclick="deleteSelectedFlow(${flow.FLOW_ID}, '${escapeHtml(flow.FLOW_NAME)}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            container.appendChild(flowCard);
        });
    }
    
    function loadSelectedFlow(flowId) {
        fetch(`/flow_designer/get_flow/${flowId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Close the load modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('load-modal'));
                if (modal) modal.hide();
                
                // Load the flow data
                loadFlowFromDatabase(data);
                showToast('Success', `Flow "${data.flow.FLOW_NAME}" loaded successfully`);
            } else {
                showToast('Error', 'Failed to load flow: ' + data.message, 'error');
            }
        })
        .catch(error => {
            showToast('Error', 'Failed to load flow: ' + error.message, 'error');
            console.error('Load flow error:', error);
        });
    }
    
    function deleteSelectedFlow(flowId, flowName) {
        if (confirm(`Are you sure you want to delete the flow "${flowName}"? This action cannot be undone.`)) {
            fetch(`/flow_designer/delete_flow/${flowId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Success', data.message);
                    // Reload the flows list
                    loadSavedFlows();
                } else {
                    showToast('Error', 'Failed to delete flow: ' + data.message, 'error');
                }
            })
            .catch(error => {
                showToast('Error', 'Failed to delete flow: ' + error.message, 'error');
                console.error('Delete flow error:', error);
            });
        }
    }
    
    function loadFlowFromDatabase(data) {
        console.log('Loading flow from database:', data);
        
        try {
            // Clear current flow
            clearCanvas();
            
            // Set current flow data
            if (data.flow) {
                currentFlow = {
                    id: data.flow.FLOW_ID,
                    name: data.flow.FLOW_NAME,
                    description: data.flow.DESCRIPTION,
                    version: data.flow.VERSION
                };
                console.log('Current flow set to:', currentFlow);
            }
        
            // Create node ID mapping for connections
            const nodeIdMap = {};
            let maxNodeId = 0;
        
            // Load nodes
            if (data.nodes && Array.isArray(data.nodes)) {
                console.log('Loading nodes:', data.nodes.length);
                data.nodes.forEach((nodeData, index) => {
                    console.log(`Loading node ${index + 1}:`, nodeData);
                    
                    const newNodeId = nextNodeId++;
                    maxNodeId = Math.max(maxNodeId, newNodeId);
                    
                    const node = {
                        id: newNodeId,
                        type: nodeData.NODE_TYPE,
                        referenceId: nodeData.REFERENCE_ID,
                        name: nodeData.LABEL,
                        x: nodeData.POSITION_X,
                        y: nodeData.POSITION_Y,
                        width: nodeData.WIDTH || 150,
                        height: nodeData.HEIGHT || 60,
                        settings: JSON.parse(nodeData.CUSTOM_SETTINGS || '{}')
                    };
                    
                    nodeIdMap[nodeData.NODE_ID] = newNodeId;
                    nodes.push(node);
                    
                    // Create visual element
                    try {
                        renderNode(node);
                        console.log(`Node ${node.id} rendered successfully`);
                    } catch (error) {
                        console.error(`Error rendering node ${node.id}:`, error);
                    }
                });
                
                nextNodeId = maxNodeId + 1;
                console.log('All nodes loaded. Next node ID:', nextNodeId);
            }
        
            // Load connections
            if (data.connections && Array.isArray(data.connections)) {
                console.log('Loading connections:', data.connections.length);
                data.connections.forEach((connData, index) => {
                    console.log(`Loading connection ${index + 1}:`, connData);
                    
                    const sourceId = nodeIdMap[connData.SOURCE_NODE_ID];
                    const targetId = nodeIdMap[connData.TARGET_NODE_ID];
                    
                    if (sourceId && targetId) {
                        const connection = {
                            id: connections.length + 1,
                            sourceId: sourceId,
                            targetId: targetId,
                            type: connData.CONNECTION_TYPE || 'DEFAULT',
                            condition: connData.CONDITION_EXPRESSION || '',
                            label: connData.LABEL || ''
                        };
                        
                        connections.push(connection);
                        
                        try {
                            renderConnection(connection);
                            console.log(`Connection ${connection.id} rendered successfully`);
                        } catch (error) {
                            console.error(`Error rendering connection ${connection.id}:`, error);
                        }
                    } else {
                        console.warn(`Skipping connection - invalid node IDs: ${connData.SOURCE_NODE_ID} -> ${connData.TARGET_NODE_ID}`);
                    }
                });
            }
            
            console.log('Flow loading completed successfully');
            showToast('Success', 'Flow loaded successfully');
            
        } catch (error) {
            console.error('Error loading flow from database:', error);
            showToast('Error', 'Failed to load flow: ' + error.message, 'error');
        }
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function validateFlow() {
        const issues = [];
        
        // Check if there are any nodes
        if (nodes.length === 0) {
            issues.push('Flow has no nodes');
        }
        
        // Check for disconnected nodes
        const connectedNodeIds = new Set();
        connections.forEach(conn => {
            connectedNodeIds.add(conn.sourceId);
            connectedNodeIds.add(conn.targetId);
        });
        
        const disconnectedNodes = nodes.filter(node => !connectedNodeIds.has(node.id));
        if (disconnectedNodes.length > 0 && nodes.length > 1) {
            issues.push(`${disconnectedNodes.length} node(s) are not connected`);
        }
        
        // Check for cycles (basic check)
        if (hasCircularDependency()) {
            issues.push('Flow contains circular dependencies');
        }
        
        if (issues.length > 0) {
            showToast('Validation Issues', issues.join('. '), 'warning');
        } else {
            showToast('Success', 'Flow validation passed successfully');
        }
    }
    
    function hasCircularDependency() {
        const visited = new Set();
        const recursionStack = new Set();
        
        function dfs(nodeId) {
            if (recursionStack.has(nodeId)) return true;
            if (visited.has(nodeId)) return false;
            
            visited.add(nodeId);
            recursionStack.add(nodeId);
            
            const outgoingConnections = connections.filter(conn => conn.sourceId === nodeId);
            for (const conn of outgoingConnections) {
                if (dfs(conn.targetId)) return true;
            }
            
            recursionStack.delete(nodeId);
            return false;
        }
        
        for (const node of nodes) {
            if (dfs(node.id)) return true;
        }
        
        return false;
    }
    
    function importFlow() {
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
                        loadFlowData(flowData);
                        showToast('Success', 'Flow imported successfully');
                    } catch (error) {
                        showToast('Error', 'Failed to import flow: Invalid file format', 'error');
                        console.error('Import error:', error);
                    }
                };
                
                reader.readAsText(file);
            }
        });
        
        fileInput.click();
    }
    
    function exportFlow() {
        if (nodes.length === 0) {
            showToast('Warning', 'No flow to export. Please create a flow first.', 'warning');
            return;
        }
        
        const flowData = {
            flow: {
                id: currentFlow.id,
                name: currentFlow.name,
                description: currentFlow.description,
                version: currentFlow.version,
                exportDate: new Date().toISOString()
            },
            nodes: nodes,
            connections: connections
        };
        
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(flowData, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", `${currentFlow.name || 'flow'}.json`);
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
        
        showToast('Success', 'Flow exported successfully');
    }
    
    function loadFlowData(flowData) {
        // Clear current flow
        clearCanvas();
        
        // Set current flow data
        if (flowData.flow) {
            currentFlow = {
                id: flowData.flow.id || null,
                name: flowData.flow.name || '',
                description: flowData.flow.description || '',
                version: flowData.flow.version || 1
            };
        }
        
        // Load nodes
        if (flowData.nodes && Array.isArray(flowData.nodes)) {
            let highestId = 0;
            
            flowData.nodes.forEach(nodeData => {
                const node = addNode(
                    nodeData.type,
                    nodeData.referenceId,
                    nodeData.name,
                    nodeData.x,
                    nodeData.y
                );
                
                node.width = nodeData.width || 150;
                node.height = nodeData.height || 60;
                node.settings = nodeData.settings || {};
                
                highestId = Math.max(highestId, node.id);
            });
            
            nextNodeId = highestId + 1;
        }
        
        // Load connections
        if (flowData.connections && Array.isArray(flowData.connections)) {
            flowData.connections.forEach(connData => {
                addConnection(connData.sourceId, connData.targetId, connData.type);
            });
        }
        
        showToast('Success', 'Flow loaded successfully');
    }
    
    function clearCanvas() {
        // Clear arrays
        nodes = [];
        connections = [];
        nextNodeId = 1;
        selectedNode = null;
        
        // Clear DOM elements
        const canvasNodes = document.querySelectorAll('.component-node');
        canvasNodes.forEach(node => node.remove());
        
        // Clear connections (keep defs)
        const svgChildren = Array.from(connectionsContainer.children);
        svgChildren.forEach(child => {
            if (child.tagName !== 'defs') {
                child.remove();
            }
        });
        
        // Reset properties panel
        hideNodeProperties();
        
        // Reset current flow
        currentFlow = {
            id: null,
            name: '',
            description: '',
            version: 1
        };
    }
    
    function updateSvgContainerSize() {
        if (connectionsContainer && canvas) {
            connectionsContainer.setAttribute('width', canvas.clientWidth);
            connectionsContainer.setAttribute('height', canvas.clientHeight);
        }
    }
    
    function loadFlowFromId() {
        const urlParams = new URLSearchParams(window.location.search);
        const flowId = urlParams.get('flowId');
        
        if (flowId) {
            fetch(`/flow_designer/get_flow/${flowId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        loadFlowFromDatabase(data);
                    }
                })
                .catch(error => {
                    console.error('Error loading flow from URL:', error);
                });
        }
    }
    
    function deleteSelectedNode() {
        if (selectedNode) {
            const nodeId = selectedNode.id;
            
            // Remove connections involving this node
            connections = connections.filter(conn => {
                if (conn.sourceId === nodeId || conn.targetId === nodeId) {
                    const connectionElement = document.getElementById(`connection-${conn.id}`);
                    if (connectionElement) {
                        connectionElement.remove();
                    }
                    return false;
                }
                return true;
            });
            
            // Remove the node
            nodes = nodes.filter(node => node.id !== nodeId);
            
            // Remove DOM element
            const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
            if (nodeElement) {
                nodeElement.remove();
            }
            
            // Deselect the node
            deselectNode();
            
            showToast('Success', 'Node deleted successfully');
        }
    }
    
    function showToast(title, message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : type === 'info' ? 'info' : 'success'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.appendChild(toast);
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }
    
    // Expose functions globally for onclick handlers
    window.loadSelectedFlow = loadSelectedFlow;
    window.deleteSelectedFlow = deleteSelectedFlow;
    window.createConnectionWithType = createConnectionWithType;
    window.closeConnectionTypeMenu = closeConnectionTypeMenu;
    window.closeNodeContextMenu = closeNodeContextMenu;
    window.quickConnect = quickConnect;
    window.deleteNodeById = deleteNodeById;
});