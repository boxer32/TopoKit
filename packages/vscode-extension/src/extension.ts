/**
 * TopoKit VS Code Extension
 * Main extension entry point
 */

import * as vscode from 'vscode';
import { PackExplorerProvider } from './views/packExplorer';
import { LintProvider } from './providers/lintProvider';
import { ContractValidationProvider } from './providers/contractValidationProvider';
import { GraphViewProvider } from './views/graphView';
import { registerCommands } from './commands/index';

let packExplorerProvider: PackExplorerProvider;
let lintProvider: LintProvider;
let contractValidationProvider: ContractValidationProvider;
let graphViewProvider: GraphViewProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log('TopoKit extension is now active');

    // Initialize providers
    packExplorerProvider = new PackExplorerProvider(context);
    lintProvider = new LintProvider();
    contractValidationProvider = new ContractValidationProvider();
    graphViewProvider = new GraphViewProvider(context);

    // Register tree view
    const treeView = vscode.window.createTreeView('topokitPackExplorer', {
        treeDataProvider: packExplorerProvider,
        showCollapseAll: true
    });

    context.subscriptions.push(treeView);

    // Register document providers
    const lintOnSave = vscode.workspace.getConfiguration('topokit').get<boolean>('lintOnSave', true);
    if (lintOnSave) {
        const watcher = vscode.workspace.createFileSystemWatcher('**/topology/**/*.{yaml,yml,json}');
        watcher.onDidChange(async (uri) => {
            await lintProvider.validateDocument(uri);
        });
        context.subscriptions.push(watcher);
    }

    // Register text document providers
    context.subscriptions.push(
        vscode.languages.registerDocumentFormattingEditProvider(
            { scheme: 'file', pattern: '**/topology/**/*.yaml' },
            lintProvider
        )
    );

    // Register inline validation
    context.subscriptions.push(
        vscode.languages.registerHoverProvider(
            { scheme: 'file', pattern: '**/topology/**/*.{yaml,json}' },
            contractValidationProvider
        )
    );

    // Register commands
    const commands = registerCommands(
        packExplorerProvider,
        graphViewProvider,
        contractValidationProvider,
        context
    );
    commands.forEach(cmd => context.subscriptions.push(cmd));

    // Show graph view on workspace open if topology detected
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (workspaceFolders) {
        for (const folder of workspaceFolders) {
            const topologyPath = vscode.Uri.joinPath(folder.uri, 'topology');
            vscode.workspace.fs.stat(topologyPath).then(
                () => {
                    vscode.commands.executeCommand('topokit.showGraph');
                },
                () => {
                    // Topology folder doesn't exist, ignore
                }
            );
        }
    }

    return {
        packExplorerProvider,
        lintProvider,
        contractValidationProvider,
        graphViewProvider
    };
}

export function deactivate() {
    console.log('TopoKit extension is now deactivated');
}

