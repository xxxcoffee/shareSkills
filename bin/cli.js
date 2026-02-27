#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

const SKILLS_DIR = path.join(os.homedir(), '.claude', 'skills');
const REPO_URL = 'git@github.com:xxxcoffee/shareSkills.git';

function showHelp() {
  console.log(`
ShareSkills CLI - Install Claude Code skills

Usage:
  npx shareskills install [skill-name]    Install a specific skill or all skills
  npx shareskills list                    List available skills
  npx shareskills --help                  Show this help message

Examples:
  npx shareskills install                 Install all skills
  npx shareskills install ali-log         Install only ali-log skill
  npx shareskills list                    Show available skills
`);
}

function listSkills() {
  const skillsPath = path.join(__dirname, '..', 'skills');
  if (!fs.existsSync(skillsPath)) {
    console.log('No skills found in local repository.');
    return;
  }
  
  const skills = fs.readdirSync(skillsPath).filter(dir => {
    return fs.statSync(path.join(skillsPath, dir)).isDirectory();
  });
  
  console.log('\nAvailable Skills:');
  console.log('=================');
  skills.forEach(skill => {
    console.log(`  • ${skill}`);
  });
  console.log('');
}

function installSkill(skillName) {
  const sourcePath = path.join(__dirname, '..', 'skills', skillName);
  const targetPath = path.join(SKILLS_DIR, skillName);
  
  if (!fs.existsSync(sourcePath)) {
    console.error(`Error: Skill "${skillName}" not found.`);
    process.exit(1);
  }
  
  // Create skills directory if not exists
  if (!fs.existsSync(SKILLS_DIR)) {
    fs.mkdirSync(SKILLS_DIR, { recursive: true });
    console.log(`Created directory: ${SKILLS_DIR}`);
  }
  
  // Check if already exists
  if (fs.existsSync(targetPath)) {
    console.log(`Skill "${skillName}" already exists. Updating...`);
    fs.rmSync(targetPath, { recursive: true });
  }
  
  // Copy skill
  copyRecursive(sourcePath, targetPath);
  console.log(`✓ Installed: ${skillName}`);
}

function installAllSkills() {
  const skillsPath = path.join(__dirname, '..', 'skills');
  if (!fs.existsSync(skillsPath)) {
    console.error('Error: No skills directory found.');
    process.exit(1);
  }
  
  const skills = fs.readdirSync(skillsPath).filter(dir => {
    return fs.statSync(path.join(skillsPath, dir)).isDirectory();
  });
  
  console.log(`\nInstalling ${skills.length} skill(s)...\n`);
  skills.forEach(skill => installSkill(skill));
  console.log('\n✓ All skills installed successfully!');
}

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    fs.readdirSync(src).forEach(child => {
      copyRecursive(path.join(src, child), path.join(dest, child));
    });
  } else {
    fs.copyFileSync(src, dest);
  }
}

// Main
const args = process.argv.slice(2);

if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
  showHelp();
  process.exit(0);
}

if (args[0] === 'list') {
  listSkills();
} else if (args[0] === 'install') {
  if (args[1]) {
    installSkill(args[1]);
  } else {
    installAllSkills();
  }
} else {
  console.error(`Unknown command: ${args[0]}`);
  showHelp();
  process.exit(1);
}
