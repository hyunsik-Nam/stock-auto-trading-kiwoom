---
applyTo: "**"
---

# Project general coding standards

## Naming Conventions

- Use PascalCase for component names, interfaces, and type aliases
- Use camelCase for variables, functions, and methods
- Prefix private class members with underscore (\_)
- Use ALL_CAPS for constants

## Code Documentation

- Write comments in Korean for all functions and classes
- Use Korean variable names when appropriate for domain-specific terms
- Include Korean descriptions for complex business logic
- Document API endpoints and data structures in Korean

## Commit Messages

- Write commit messages in Korean
- Use conventional commit format: `타입(스코프): 설명`
- Examples: `추가(auth): 로그인 기능 구현`, `수정(ui): 버튼 스타일 개선`

## Error Handling

- Use try/catch blocks for async operations
- Implement proper error boundaries in React components
- Always log errors with contextual information
