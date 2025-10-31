/**
 * Pack Explorer Tree View Provider
 * Displays topology pack structure in VS Code explorer
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as yaml from 'yaml';

export class PackExplorerProvider implements vscode.TreeDataProvider<PackItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<PackItem | undefined | null | void> = new vscode.EventEmitter<PackItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<PackItem | undefined | null | void> = this._onDidChangeTreeData.event;

    constructor(private context: vscode.ExtensionContext) {}

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: PackItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: PackItem): Promise<PackItem[]> {
        if (!vscode.workspace.workspaceFolders) {
            return [];
        }

        const workspaceRoot = vscode.workspace.workspaceFolders[0].uri.fsPath;
        const topologyPath = path.join(workspaceRoot, 'topology');

        if (!element) {
            // Root level - find all topology folders
            return this.getTopologyFolders(workspaceRoot);
        }

        if (element.contextValue === 'topologyFolder') {
            // Topology folder - show nodes, edges, contracts, guardrails
            return this.getTopologyContents(element.path);
        }

        if (element.contextValue === 'contractsFolder') {
            // Contracts folder - show contract files
            return this.getContractFiles(element.path);
        }

        return [];
    }

    private async getTopologyFolders(workspaceRoot: string): Promise<PackItem[]> {
        const items: PackItem[] = [];
        
        // Check for topology folder in root
        const topologyPath = path.join(workspaceRoot, 'topology');
        if (fs.existsSync(topologyPath)) {
            items.push(new PackItem(
                'Topology',
                vscode.TreeItemCollapsibleState.Collapsed,
                topologyPath,
                'topologyFolder'
            ));
        }

        return items;
    }

    private async getTopologyContents(topologyPath: string): Promise<PackItem[]> {
        const items: PackItem[] = [];

        // Nodes
        const nodesPath = path.join(topologyPath, 'nodes.yaml');
        if (fs.existsSync(nodesPath)) {
            items.push(new PackItem(
                'Nodes',
                vscode.TreeItemCollapsibleState.None,
                nodesPath,
                'nodesFile',
                vscode.ThemeIcon.File
            ));
        }

        // Edges
        const edgesPath = path.join(topologyPath, 'edges.yaml');
        if (fs.existsSync(edgesPath)) {
            items.push(new PackItem(
                'Edges',
                vscode.TreeItemCollapsibleState.None,
                edgesPath,
                'edgesFile',
                vscode.ThemeIcon.File
            ));
        }

        // Contracts folder
        const contractsPath = path.join(topologyPath, 'contracts');
        if (fs.existsSync(contractsPath)) {
            items.push(new PackItem(
                'Contracts',
                vscode.TreeItemCollapsibleState.Collapsed,
                contractsPath,
                'contractsFolder',
                vscode.ThemeIcon.Folder
            ));
        }

        // Guardrails
        const guardrailsPath = path.join(topologyPath, 'guardrails.yaml');
        if (fs.existsSync(guardrailsPath)) {
            items.push(new PackItem(
                'Guardrails',
                vscode.TreeItemCollapsibleState.None,
                guardrailsPath,
                'guardrailsFile',
                vscode.ThemeIcon.File
            ));
        }

        return items;
    }

    private async getContractFiles(contractsPath: string): Promise<PackItem[]> {
        const items: PackItem[] = [];

        if (!fs.existsSync(contractsPath)) {
            return items;
        }

        const files = fs.readdirSync(contractsPath);
        for (const file of files) {
            if (file.endsWith('.json')) {
                const filePath = path.join(contractsPath, file);
                items.push(new PackItem(
                    file,
                    vscode.TreeItemCollapsibleState.None,
                    filePath,
                    'contract',
                    vscode.ThemeIcon.File
                ));
            }
        }

        return items;
    }
}

class PackItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly path: string,
        public readonly contextValue: string,
        public readonly icon?: vscode.ThemeIcon
    ) {
        super(label, collapsibleState);

        this.tooltip = this.path;
        this.command = {
            command: 'vscode.open',
            title: 'Open File',
            arguments: [vscode.Uri.file(this.path)]
        };
    }
}

