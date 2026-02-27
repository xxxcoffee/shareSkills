# ShareSkills

English | [简体中文](./README_CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A collection of reusable Claude Code skills for enhanced development productivity.

## Skills Overview

### ali-log

Alibaba Cloud Log Service (SLS) query tool supporting log retrieval, analysis, query builder, and SQL templates.

**Features:**
- Pull raw logs (pull_logs)
- Query and analyze logs (query_logs)
- Get cursor by time (get_cursor)
- Query builder for convenient query construction
- SQL analysis builder with chainable API
- Query templates for common scenarios
- Complete SQL function reference

[View Details](./skills/ali-log/)

## Installation

### Method 1: Clone and Copy

```bash
# Clone the repository
git clone git@github.com:xxxcoffee/shareSkills.git

# Copy skills to Claude Code skills directory
cp -r shareSkills/skills/ali-log ~/.claude/skills/
```

### Method 2: Direct Download

```bash
# Create skills directory if not exists
mkdir -p ~/.claude/skills

# Download and extract specific skill
cd ~/.claude/skills
git clone --depth 1 --filter=blob:none --sparse git@github.com:xxxcoffee/shareSkills.git temp
cd temp
git sparse-checkout set skills/ali-log
cp -r skills/ali-log ../
cd ..
rm -rf temp
```

### Method 3: Using npx (Coming Soon)

```bash
# Install all skills
npx shareskills install

# Install specific skill
npx shareskills install ali-log
```

## Skill Structure

```
~/.claude/skills/
└── ali-log/
    ├── SKILL.md              # Skill documentation
    ├── ali_log.py           # Core implementation
    ├── query_builder.py     # Query/SQL builder
    ├── QUERY_REFERENCE.md   # Function reference
    ├── README.md            # Skill readme (EN)
    ├── README_CN.md         # Skill readme (CN)
    └── requirements.txt     # Dependencies
```

## Development

### Adding a New Skill

1. Create a new directory under `skills/`
2. Add `SKILL.md` with skill definition
3. Implement your skill logic
4. Add documentation and examples
5. Update main README.md

### Skill Guidelines

- Skills should be self-contained
- Include clear documentation in `SKILL.md`
- Provide usage examples
- List all dependencies in `requirements.txt`
- Follow existing code style

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-skill`)
3. Commit your changes (`git commit -m 'Add some amazing skill'`)
4. Push to the branch (`git push origin feature/amazing-skill`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## Support

If you encounter any issues or have questions:

- Open an issue on GitHub
- Check the skill's README for specific usage details
- Review the QUERY_REFERENCE.md for SQL function documentation

## Acknowledgments

- Built for [Claude Code](https://claude.ai/code)
- Powered by Alibaba Cloud Log Service SDK
- Inspired by the Claude Code community