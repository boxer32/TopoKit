/**
 * Contract Validation Provider for inline validation
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export class ContractValidationProvider implements vscode.HoverProvider {
    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.Hover> {
        const wordRange = document.getWordRangeAtPosition(position);
        if (!wordRange) {
            return null;
        }

        const word = document.getText(wordRange);
        const line = document.lineAt(position.line);

        // Check if we're in a contract reference
        if (this.isContractReference(word, line.text)) {
            const contractInfo = this.getContractInfo(word, document.uri.fsPath);
            if (contractInfo) {
                return new vscode.Hover(contractInfo);
            }
        }

        return null;
    }

    private isContractReference(word: string, lineText: string): boolean {
        // Simple heuristic - check if word appears in contracts context
        return lineText.includes('contract') || lineText.includes('contracts:');
    }

    private getContractInfo(contractName: string, documentPath: string): vscode.MarkdownString | null {
        // Try to find contract file
        const topologyDir = this.findTopologyDir(documentPath);
        if (!topologyDir) {
            return null;
        }

        const contractsDir = path.join(topologyDir, 'contracts');
        const contractFile = path.join(contractsDir, `${contractName}.json`);

        if (!fs.existsSync(contractFile)) {
            return null;
        }

        try {
            const contractContent = JSON.parse(fs.readFileSync(contractFile, 'utf-8'));
            const markdown = new vscode.MarkdownString();
            markdown.appendMarkdown(`### Contract: ${contractName}\n\n`);
            markdown.appendMarkdown(`**Version:** ${contractContent.version || '1.0.0'}\n\n`);
            
            if (contractContent.description) {
                markdown.appendMarkdown(`**Description:** ${contractContent.description}\n\n`);
            }

            if (contractContent.input_schema) {
                markdown.appendMarkdown(`**Input Schema:** Defined\n`);
            }

            if (contractContent.output_schema) {
                markdown.appendMarkdown(`**Output Schema:** Defined\n`);
            }

            return markdown;
        } catch (error) {
            return null;
        }
    }

    private findTopologyDir(startPath: string): string | null {
        let currentPath = startPath;
        
        while (currentPath !== path.dirname(currentPath)) {
            if (path.basename(currentPath) === 'topology') {
                return currentPath;
            }
            currentPath = path.dirname(currentPath);
        }

        // Check for topology folder in workspace
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders) {
            const topologyPath = path.join(workspaceFolders[0].uri.fsPath, 'topology');
            if (fs.existsSync(topologyPath)) {
                return topologyPath;
            }
        }

        return null;
    }
}

