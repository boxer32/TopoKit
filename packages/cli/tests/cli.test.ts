import { describe, it, expect } from 'vitest';
import { execSync } from 'child_process';
import path from 'path';

describe('CLI', () => {
  const cliPath = path.join(__dirname, '../dist/index.js');

  it('should show help when no arguments provided', () => {
    const output = execSync(`node ${cliPath} --help`, { encoding: 'utf-8' });
    expect(output).toContain('TopoKit CLI');
    expect(output).toContain('Commands:');
    expect(output).toContain('init');
    expect(output).toContain('lint');
    expect(output).toContain('graph');
  });

  it('should show version', () => {
    const output = execSync(`node ${cliPath} --version`, { encoding: 'utf-8' });
    expect(output.trim()).toBe('0.1.0');
  });

  it('should initialize a project', () => {
    const tempDir = '/tmp/test-topokit-init';
    try {
      const output = execSync(`node ${cliPath} init --template rag-system --output ${tempDir}`, { 
        encoding: 'utf-8',
        cwd: '/tmp'
      });
      expect(output).toContain('TopoKit project initialized successfully');
    } finally {
      // Cleanup
      execSync(`rm -rf ${tempDir}`, { stdio: 'ignore' });
    }
  });
});
