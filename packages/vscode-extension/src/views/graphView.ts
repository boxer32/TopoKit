/**
 * Graph View Provider for interactive topology visualization
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export class GraphViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'topokitGraphView';

    private _view?: vscode.WebviewView;

    constructor(private readonly _context: vscode.ExtensionContext) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._context.extensionUri]
        };

        webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

        // Listen for messages from webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'refresh':
                    await this.refreshGraph();
                    break;
            }
        });
    }

    private async refreshGraph(): Promise<void> {
        if (!this._view) {
            return;
        }

        // Generate graph data from topology
        const graphData = await this.generateGraphData();
        
        // Send to webview
        this._view.webview.postMessage({
            command: 'updateGraph',
            data: graphData
        });
    }

    private async generateGraphData(): Promise<any> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return { nodes: [], edges: [] };
        }

        const topologyPath = path.join(workspaceFolders[0].uri.fsPath, 'topology');
        if (!fs.existsSync(topologyPath)) {
            return { nodes: [], edges: [] };
        }

        // Parse topology files
        const nodesFile = path.join(topologyPath, 'nodes.yaml');
        const edgesFile = path.join(topologyPath, 'edges.yaml');

        const nodes: any[] = [];
        const edges: any[] = [];

        if (fs.existsSync(nodesFile)) {
            const yaml = require('yaml');
            const nodesContent = fs.readFileSync(nodesFile, 'utf-8');
            const nodesData = yaml.parse(nodesContent);
            
            if (nodesData.nodes) {
                for (const node of nodesData.nodes) {
                    nodes.push({
                        id: node.id,
                        label: node.id,
                        type: node.kind || 'data'
                    });
                }
            }
        }

        if (fs.existsSync(edgesFile)) {
            const yaml = require('yaml');
            const edgesContent = fs.readFileSync(edgesFile, 'utf-8');
            const edgesData = yaml.parse(edgesContent);
            
            if (edgesData.edges) {
                for (const edge of edgesData.edges) {
                    edges.push({
                        from: edge.from || edge.from_node,
                        to: edge.to || edge.to_node,
                        id: edge.id
                    });
                }
            }
        }

        return { nodes, edges };
    }

    private getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TopoKit Graph View</title>
    <style>
        body {
            padding: 10px;
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
        }
        #graph-container {
            width: 100%;
            height: 600px;
            border: 1px solid var(--vscode-panel-border);
        }
        .graph-node {
            fill: var(--vscode-button-background);
            stroke: var(--vscode-button-foreground);
        }
        .graph-edge {
            stroke: var(--vscode-foreground);
        }
    </style>
</head>
<body>
    <h2>Topology Graph</h2>
    <div id="graph-container">
        <svg id="graph-svg" width="100%" height="100%">
            <!-- Graph will be rendered here -->
        </svg>
    </div>
    <script>
        const vscode = acquireVsCodeApi();
        
        window.addEventListener('message', event => {
            const message = event.data;
            if (message.command === 'updateGraph') {
                renderGraph(message.data);
            }
        });

        function renderGraph(data) {
            const svg = document.getElementById('graph-svg');
            svg.innerHTML = '';
            
            // Simple graph rendering
            const nodes = data.nodes || [];
            const edges = data.edges || [];
            
            // Render edges
            edges.forEach((edge, index) => {
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', (index * 50 + 50).toString());
                line.setAttribute('y1', '50');
                line.setAttribute('x2', (index * 50 + 100).toString());
                line.setAttribute('y2', '50');
                line.setAttribute('class', 'graph-edge');
                line.setAttribute('stroke-width', '2');
                svg.appendChild(line);
            });
            
            // Render nodes
            nodes.forEach((node, index) => {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', (index * 50 + 50).toString());
                circle.setAttribute('cy', '50');
                circle.setAttribute('r', '20');
                circle.setAttribute('class', 'graph-node');
                svg.appendChild(circle);
                
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', (index * 50 + 50).toString());
                text.setAttribute('y', '55');
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('fill', 'var(--vscode-foreground)');
                text.setAttribute('font-size', '10');
                text.textContent = node.id || node.label;
                svg.appendChild(text);
            });
        }
    </script>
</body>
</html>`;
    }
}

