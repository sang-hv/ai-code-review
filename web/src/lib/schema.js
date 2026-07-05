// Pure helpers to turn the ArgusReview pydantic JSON Schema into a description
// the config builder can render. No DOM here so it can be unit-tested with node.

export function deref(schema, ref) {
  return schema.$defs[ref.replace('#/$defs/', '')];
}

// A discriminated-union section (llm / vcs): provider const -> variant $ref.
export function providerMapping(schema, section) {
  const node = schema.properties[section];
  return node?.discriminator?.mapping ?? {};
}

// Collapse an optional `anyOf: [T, null]` (or a $ref) into a single leaf schema,
// preserving `format` and `enum`.
function effectiveLeaf(schema, prop) {
  if (!prop) return { type: 'string' };
  if (prop.$ref) {
    const def = deref(schema, prop.$ref);
    if (def?.enum) return { type: 'string', enum: def.enum };
    return def ?? { type: 'string' };
  }
  if (prop.anyOf) {
    // Prefer a boolean branch when present (e.g. `verify: file-path | bool`)
    // so it renders as a checkbox rather than a free-text path.
    const boolBranch = prop.anyOf.find((b) => b.type === 'boolean');
    if (boolBranch) return { ...boolBranch };
    const nonNull = prop.anyOf.find((b) => b.type !== 'null') ?? {};
    return { ...nonNull };
  }
  return prop;
}

function kindOf(leaf) {
  if (leaf.enum) return 'enum';
  if (leaf.type === 'boolean') return 'bool';
  if (leaf.type === 'integer' || leaf.type === 'number') return 'number';
  if (leaf.format === 'password') return 'password';
  return 'text';
}

// Turn a def ($ref target) into a flat list of field descriptors.
export function fieldsForRef(schema, ref, { skip = [] } = {}) {
  const def = deref(schema, ref);
  if (!def?.properties) return [];
  const required = new Set(def.required ?? []);
  const out = [];
  for (const [name, prop] of Object.entries(def.properties)) {
    if (skip.includes(name)) continue;
    const leaf = effectiveLeaf(schema, prop);
    out.push({
      name,
      kind: kindOf(leaf),
      options: leaf.enum ?? null,
      required: required.has(name),
      default: prop.default ?? leaf.default ?? null,
      isConst: prop.const !== undefined,
      constValue: prop.const,
    });
  }
  return out;
}

// For a provider variant, return its sub-object refs (meta, http_client, pipeline...).
export function variantGroups(schema, section, provider) {
  const ref = providerMapping(schema, section)[provider];
  if (!ref) return [];
  const variant = deref(schema, ref);
  const groups = [];
  for (const [name, prop] of Object.entries(variant.properties)) {
    if (name === 'provider' || name === 'pricing_file' || name === 'pagination') continue;
    if (prop.$ref) groups.push({ name, ref: prop.$ref });
  }
  return groups;
}

export function providerKeys(schema, section) {
  return Object.keys(providerMapping(schema, section)).sort();
}

export function enumValues(schema, ref) {
  return deref(schema, ref)?.enum ?? [];
}
