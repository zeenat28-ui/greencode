/**
 * GreenCode Energy & Carbon Linter — Official VS Code Extension (v2.0.0).
 *
 * Provides real-time Language Server Protocol (LSP) diagnostics and Quick Fixes:
 * - Flags nested loops, SDK client instantiation in loops, uncached network calls, and DB cursors.
 * - Displays live team carbon budget status from /api/energy/budgets.
 * - Provides 1-click Quick Fix code actions backed by POST /api/refactor.
 */

const vscode = require('vscode');
const http = require('http');
const https = require('https');

let diagnosticCollection;

function requestJson(urlString, method = 'GET', bodyObj = null) {
    return new Promise((resolve, reject) => {
        const parsedUrl = new URL(urlString);
        const client = parsedUrl.protocol === 'https:' ? https : http;
        const payload = bodyObj ? JSON.stringify(bodyObj) : null;
        const options = {
            hostname: parsedUrl.hostname,
            port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 8000),
            path: parsedUrl.pathname + (parsedUrl.search || ''),
            method,
            headers: {
                'Content-Type': 'application/json',
                ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {})
            },
            timeout: 5000
        };

        const req = client.request(options, res => {
            let responseBody = '';
            res.on('data', chunk => { responseBody += chunk; });
            res.on('end', () => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    try {
                        resolve(JSON.parse(responseBody));
                    } catch (e) {
                        reject(e);
                    }
                } else {
                    reject(new Error(`HTTP ${res.statusCode}`));
                }
            });
        });

        req.on('error', reject);
        if (payload) req.write(payload);
        req.end();
    });
}

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    diagnosticCollection = vscode.languages.createDiagnosticCollection('greencode');
    context.subscriptions.push(diagnosticCollection);

    const changeSubscription = vscode.workspace.onDidChangeTextDocument(event => {
        const config = vscode.workspace.getConfiguration('greencode');
        if (config.get('enableRealTimeLinting', true)) {
            lintDocument(event.document);
        }
    });
    context.subscriptions.push(changeSubscription);

    vscode.workspace.onDidOpenTextDocument(doc => {
        lintDocument(doc);
    });

    const lintCmd = vscode.commands.registerCommand('greencode.lintWorkspace', () => {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            lintDocument(editor.document, true);
        } else {
            vscode.window.showInformationMessage('No active editor open to lint.');
        }
    });
    context.subscriptions.push(lintCmd);

    const debtCmd = vscode.commands.registerCommand('greencode.showEnergyDebt', () => {
        showEnergyDebtModal();
    });
    context.subscriptions.push(debtCmd);

    const quickFixCmd = vscode.commands.registerCommand(
        'greencode.applyQuickFix',
        async (document, range, violationCode) => {
            await applyLiveRefactor(document, range, violationCode);
        }
    );
    context.subscriptions.push(quickFixCmd);

    const codeActionProvider = vscode.languages.registerCodeActionsProvider(
        { scheme: 'file' },
        {
            provideCodeActions(document, range, context) {
                const actions = [];
                for (const diag of context.diagnostics) {
                    if (diag.source === 'GreenCode Energy Linter') {
                        const action = new vscode.CodeAction(
                            `GreenCode: Refactor '${diag.code || 'violation'}' via Live AST/Bedrock`,
                            vscode.CodeActionKind.QuickFix
                        );
                        action.command = {
                            command: 'greencode.applyQuickFix',
                            title: 'Apply GreenCode Refactoring',
                            arguments: [document, diag.range, String(diag.code || 'inefficient_loop')]
                        };
                        action.diagnostics = [diag];
                        action.isPreferred = true;
                        actions.push(action);
                    }
                }
                return actions;
            }
        },
        { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }
    );
    context.subscriptions.push(codeActionProvider);

    if (vscode.window.activeTextEditor) {
        lintDocument(vscode.window.activeTextEditor.document);
    }
}

async function lintDocument(document, isExplicit = false) {
    if (!document || document.isUntitled) return;

    const sourceCode = document.getText();
    const languageId = document.languageId;
    const config = vscode.workspace.getConfiguration('greencode');
    const apiUrl = config.get('apiUrl', 'http://localhost:8000');

    try {
        const data = await requestJson(`${apiUrl}/api/enterprise/linter/diagnostics`, 'POST', {
            source_code: sourceCode,
            language: languageId
        });
        updateDiagnostics(document, data.diagnostics || []);
        if (isExplicit) {
            const count = (data.diagnostics || []).length;
            vscode.window.showInformationMessage(
                `GreenCode Audit Complete: Found ${count} energy anti-patterns in ${document.fileName}.`
            );
        }
    } catch (err) {
        if (isExplicit) {
            vscode.window.showWarningMessage(`GreenCode server unreachable at ${apiUrl}: ${err.message}`);
        }
    }
}

function updateDiagnostics(document, rawDiagnostics) {
    const diagnostics = [];

    for (const item of rawDiagnostics) {
        const line = Math.max(0, (item.line_number || 1) - 1);
        const endLine = Math.max(line, (item.end_line_number || item.line_number || 1) - 1);
        const range = new vscode.Range(line, 0, endLine, 120);

        let severity = vscode.DiagnosticSeverity.Warning;
        if (item.severity === 'ERROR' || item.severity === 'CRITICAL') {
            severity = vscode.DiagnosticSeverity.Error;
        } else if (item.severity === 'INFORMATION' || item.severity === 'LOW') {
            severity = vscode.DiagnosticSeverity.Information;
        }

        const message = `[GreenCode] ${item.title}: ${item.suggested_fix} (~$${item.annual_cost_usd}/yr, ${item.annual_co2_kg} kg CO2e)`;
        const diagnostic = new vscode.Diagnostic(range, message, severity);
        diagnostic.source = 'GreenCode Energy Linter';
        diagnostic.code = item.code;

        diagnostics.push(diagnostic);
    }

    diagnosticCollection.set(document.uri, diagnostics);
}

async function applyLiveRefactor(document, range, violationCode) {
    const config = vscode.workspace.getConfiguration('greencode');
    const apiUrl = config.get('apiUrl', 'http://localhost:8000');
    const snippet = document.getText(range) || document.getText();

    try {
        const data = await requestJson(`${apiUrl}/api/refactor`, 'POST', {
            source_code: snippet,
            language: document.languageId || 'python',
            violation_type: violationCode,
            file_path: document.fileName
        });
        if (data && data.refactored_code) {
            const edit = new vscode.WorkspaceEdit();
            const targetRange = document.getText(range)
                ? range
                : new vscode.Range(0, 0, document.lineCount, 0);
            edit.replace(document.uri, targetRange, data.refactored_code);
            await vscode.workspace.applyEdit(edit);
            vscode.window.showInformationMessage(
                `GreenCode Refactoring Applied (${data.estimated_energy_reduction_pct || 45}% estimated energy reduction).`
            );
        }
    } catch (err) {
        vscode.window.showWarningMessage(`Failed to refactor via ${apiUrl}/api/refactor: ${err.message}`);
    }
}

async function showEnergyDebtModal() {
    const config = vscode.workspace.getConfiguration('greencode');
    const apiUrl = config.get('apiUrl', 'http://localhost:8000');

    try {
        const data = await requestJson(`${apiUrl}/api/energy/budgets?org_id=1&team_id=core-infra`, 'GET');
        const consumed = Number(data.consumed_kg_co2e || 0).toFixed(2);
        const limit = Number(data.monthly_budget_kg_co2e || 500).toFixed(2);
        const pct = Number(data.consumption_pct || 0).toFixed(1);
        const status = data.alert_level || 'HEALTHY';
        vscode.window.showInformationMessage(
            `GreenCode Live Team Carbon Budget (core-infra): ${consumed} / ${limit} kg CO2e (${pct}% used — Status: ${status}).`
        );
    } catch (err) {
        vscode.window.showWarningMessage(
            `Could not fetch live carbon budget from ${apiUrl}/api/energy/budgets (${err.message}).`
        );
    }
}

function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
        diagnosticCollection.dispose();
    }
}

module.exports = {
    activate,
    deactivate
};
