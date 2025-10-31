/**
 * Command registration for TopoKit extension
 */

import * as vscode from 'vscode';
import { PackExplorerProvider } from '../views/packExplorer';
import { GraphViewProvider } from '../views/graphView';
import { ContractValidationProvider } from '../providers/contractValidationProvider';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export function registerCommands(
    packExplorer: PackExplorerProvider,
    graphView: GraphViewProvider,
    contractValidator: ContractValidationProvider,
    context: vscode.ExtensionContext
): vscode.Disposable[] {
    const commands: vscode.Disposable[] = [];

    // Refresh Pack Explorer
    commands.push(
        vscode.commands.registerCommand('topokit.packExplorer.refresh', () => {
            packExplorer.refresh();
        })
    );

    // Validate Contract
    commands.push(
        vscode.commands.registerCommand('topokit.validateContract', async (uri?: vscode.Uri) => {
            const fileUri = uri || vscode.window.activeTextEditor?.document.uri;
            if (!fileUri) {
                vscode.window.showWarningMessage('No file selected for validation');
                return;
            }

            try {
                const workspaceFolder = vscode.workspace.getWorkspaceFolder(fileUri);
                if (!workspaceFolder) {
                    return;
                }

                // Try to run topokit lint
                const topologyDir = fileUri.fsPath.includes('topology') 
                    ? require('path').dirname(fileUri.fsPath)
                    : require('path').join(workspaceFolder.uri.fsPath, 'topology');

                try {
                    const { stdout } = await execAsync(
                        `topokit lint "${topologyDir}"`,
                        { cwd: workspaceFolder.uri.fsPath, timeout: 5000 }
                    );
                    vscode.window.showInformationMessage('Contract validation passed');
                } catch (error: any) {
                    vscode.window.showErrorMessage(`Validation failed: ${error.message}`);
                }
            } catch (error: any) {
                vscode.window.showErrorMessage(`Error: ${error.message}`);
            }
        })
    );

    // Run Tests
    commands.push(
        vscode.commands.registerCommand('topokit.runTests', async () => {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders) {
                vscode.window.showWarningMessage('No workspace folder open');
                return;
            }

            try {
                const topologyDir = require('path').join(workspaceFolders[0].uri.fsPath, 'topology');
                const { stdout } = await execAsync(
                    `topokit eval --pack-dir "${topologyDir}"`,
                    { cwd: workspaceFolders[0].uri.fsPath, timeout: 30000 }
                );
                
                // Show output in output channel
                const outputChannel = vscode.window.createOutputChannel('TopoKit Tests');
                outputChannel.clear();
                outputChannel.append(stdout);
                outputChannel.show();
            } catch (error: any) {
                vscode.window.showErrorMessage(`Tests failed: ${error.message}`);
            }
        })
    );

    // Show Graph View
    commands.push(
        vscode.commands.registerCommand('topokit.showGraph', () => {
            vscode.commands.executeCommand('topokitGraphView.focus');
        })
    );

    // Debug Console
    commands.push(
        vscode.commands.registerCommand('topokit.debugConsole', () => {
            vscode.window.showInformationMessage('Debug Console - Coming soon');
            // TODO: Implement debug console functionality
        })
    );

    return commands;
}

