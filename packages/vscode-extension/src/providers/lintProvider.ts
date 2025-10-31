/**
 * Lint Provider for lint-on-save validation
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export class LintProvider implements vscode.DocumentFormattingEditProvider {
    private diagnosticCollection: vscode.DiagnosticCollection;

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('topokit');
    }

    async validateDocument(uri: vscode.Uri): Promise<void> {
        const document = await vscode.workspace.openTextDocument(uri);
        await this.validate(document);
    }

    async validate(document: vscode.TextDocument): Promise<void> {
        if (!this.isTopologyFile(document)) {
            return;
        }

        const diagnostics: vscode.Diagnostic[] = [];

        try {
            // Check if topokit CLI is available
            const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
            if (!workspaceFolder) {
                return;
            }

            const topologyDir = path.dirname(document.uri.fsPath);
            
            // Try to run topokit lint
            try {
                const { stdout, stderr } = await execAsync(
                    `topokit lint "${topologyDir}"`,
                    { cwd: workspaceFolder.uri.fsPath, timeout: 5000 }
                );

                // Parse lint output and create diagnostics
                // This is a simplified version - real implementation would parse actual output
                if (stderr) {
                    const diagnostic = new vscode.Diagnostic(
                        new vscode.Range(0, 0, 0, 0),
                        stderr,
                        vscode.DiagnosticSeverity.Warning
                    );
                    diagnostics.push(diagnostic);
                }
            } catch (error) {
                // CLI not available or error - skip validation
                console.log('TopoKit CLI not available for linting:', error);
            }

            // Basic YAML/JSON validation
            if (document.uri.fsPath.endsWith('.yaml') || document.uri.fsPath.endsWith('.yml')) {
                try {
                    const yaml = require('yaml');
                    yaml.parse(document.getText());
                } catch (parseError: any) {
                    const line = parseError.line || 0;
                    const pos = parseError.pos || 0;
                    const diagnostic = new vscode.Diagnostic(
                        new vscode.Range(line, pos, line, pos + 1),
                        `YAML Parse Error: ${parseError.message}`,
                        vscode.DiagnosticSeverity.Error
                    );
                    diagnostics.push(diagnostic);
                }
            }

            if (document.uri.fsPath.endsWith('.json')) {
                try {
                    JSON.parse(document.getText());
                } catch (parseError: any) {
                    const line = (parseError.message.match(/line (\d+)/i)?.[1] || '1') as any;
                    const diagnostic = new vscode.Diagnostic(
                        new vscode.Range((line - 1) as number, 0, (line - 1) as number, 1),
                        `JSON Parse Error: ${parseError.message}`,
                        vscode.DiagnosticSeverity.Error
                    );
                    diagnostics.push(diagnostic);
                }
            }
        } catch (error) {
            console.error('Validation error:', error);
        }

        this.diagnosticCollection.set(document.uri, diagnostics);
    }

    async provideDocumentFormattingEdits(
        document: vscode.TextDocument,
        options: vscode.FormattingOptions,
        token: vscode.CancellationToken
    ): Promise<vscode.TextEdit[]> {
        // Basic formatting - could be enhanced with actual TopoKit formatting rules
        return [];
    }

    private isTopologyFile(document: vscode.TextDocument): boolean {
        const uri = document.uri.fsPath;
        return uri.includes('topology') && (
            uri.endsWith('.yaml') ||
            uri.endsWith('.yml') ||
            uri.endsWith('.json')
        );
    }
}

