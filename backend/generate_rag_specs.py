import os
import json
import ast

def extract_schemas(base_dir):
    schemas_dir = os.path.join(base_dir, 'app', 'schemas')
    output = []
    output.append("# Backend API Specs (RAG Context)")
    output.append("This document is auto-generated. Frontend agents must read this to understand data structures.\n")
    
    for filename in os.listdir(schemas_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            filepath = os.path.join(schemas_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
                
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    output.append(f"## Schema: `{node.name}` (from `{filename}`)")
                    fields = []
                    for child in node.body:
                        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                            field_name = child.target.id
                            # Extremely simple type extraction for context
                            field_type = ast.unparse(child.annotation) if hasattr(ast, 'unparse') else "unknown"
                            fields.append(f"- **{field_name}**: `{field_type}`")
                    
                    if fields:
                        output.extend(fields)
                    else:
                        output.append("- (No explicit fields or inherits directly)")
                    output.append("")
                    
    with open(os.path.join(base_dir, '..', '.agents', 'api_specs_rag.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    print("API Specs RAG artifact generated at .agents/api_specs_rag.md")

if __name__ == "__main__":
    extract_schemas(r"D:\projects\test-project\backend")
