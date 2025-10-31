/**
 * Validation script for frontend dashboard
 * Checks for required files, imports, and basic structure
 */

import { readdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';

interface ValidationResult {
  name: string;
  status: 'pass' | 'fail' | 'warning';
  message: string;
}

const results: ValidationResult[] = [];

function addResult(name: string, status: 'pass' | 'fail' | 'warning', message: string) {
  results.push({ name, status, message });
}

async function validateFileStructure() {
  const srcDir = join(process.cwd(), 'src');
  
  // Check core files
  const coreFiles = ['main.tsx', 'App.tsx', 'index.css', 'App.css'];
  for (const file of coreFiles) {
    const path = join(srcDir, file);
    if (existsSync(path)) {
      addResult(`Core: ${file}`, 'pass', 'File exists');
    } else {
      addResult(`Core: ${file}`, 'fail', 'File missing');
    }
  }

  // Check directories
  const requiredDirs = ['components', 'pages', 'api', 'monitoring'];
  for (const dir of requiredDirs) {
    const path = join(srcDir, dir);
    if (existsSync(path)) {
      try {
        const files = await readdir(path);
        addResult(`Directory: ${dir}`, 'pass', `${files.length} files found`);
      } catch (error) {
        addResult(`Directory: ${dir}`, 'warning', 'Directory exists but cannot read');
      }
    } else {
      addResult(`Directory: ${dir}`, 'fail', 'Directory missing');
    }
  }
}

async function validateImports() {
  const componentsDir = join(process.cwd(), 'src', 'components');
  
  try {
    const files = await readdir(componentsDir);
    const tsxFiles = files.filter(f => f.endsWith('.tsx'));
    
    for (const file of tsxFiles.slice(0, 10)) { // Check first 10
      const path = join(componentsDir, file);
      try {
        const content = await readFile(path, 'utf-8');
        
        // Check for React import
        if (content.includes("from 'react'") || content.includes('from "react"')) {
          addResult(`Import: ${file}`, 'pass', 'React import found');
        } else {
          addResult(`Import: ${file}`, 'warning', 'React import not found');
        }
        
        // Check for component export
        if (content.includes('export default') || content.includes('export function') || content.includes('export const')) {
          addResult(`Export: ${file}`, 'pass', 'Component exported');
        } else {
          addResult(`Export: ${file}`, 'warning', 'No export found');
        }
      } catch (error) {
        addResult(`Read: ${file}`, 'fail', `Cannot read file: ${error}`);
      }
    }
  } catch (error) {
    addResult('Components Directory', 'fail', `Cannot read directory: ${error}`);
  }
}

async function validateConfigFiles() {
  const configFiles = [
    'package.json',
    'tsconfig.json',
    'vite.config.ts',
    'index.html'
  ];
  
  for (const file of configFiles) {
    const path = join(process.cwd(), file);
    if (existsSync(path)) {
      addResult(`Config: ${file}`, 'pass', 'File exists');
    } else {
      addResult(`Config: ${file}`, 'fail', 'File missing');
    }
  }
}

async function main() {
  console.log('🔍 Validating Frontend Dashboard...\n');
  
  await validateConfigFiles();
  await validateFileStructure();
  await validateImports();
  
  console.log('\n📊 Validation Results:\n');
  
  const passed = results.filter(r => r.status === 'pass').length;
  const failed = results.filter(r => r.status === 'fail').length;
  const warnings = results.filter(r => r.status === 'warning').length;
  
  for (const result of results) {
    const icon = result.status === 'pass' ? '✅' : result.status === 'fail' ? '❌' : '⚠️';
    console.log(`${icon} ${result.name}: ${result.message}`);
  }
  
  console.log(`\n📈 Summary:`);
  console.log(`   ✅ Passed: ${passed}`);
  console.log(`   ❌ Failed: ${failed}`);
  console.log(`   ⚠️  Warnings: ${warnings}`);
  
  if (failed === 0) {
    console.log('\n✅ All critical validations passed!');
    process.exit(0);
  } else {
    console.log('\n❌ Some validations failed. Please review above.');
    process.exit(1);
  }
}

main().catch(console.error);

