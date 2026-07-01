# 📘 ArgusReview Configuration

ArgusReview supports multiple configuration formats and sources. All of them are automatically detected at runtime.

---

## 📂 Supported formats

- **YAML** (recommended): `.ai-review.yaml`
- **JSON**: `.ai-review.json`
- **ENV**: `.env`

👉 You can combine formats: values are loaded in order of priority.

---

## 📑 Load priority

1. **YAML** (`.ai-review.yaml` or path from `AI_REVIEW_CONFIG_FILE_YAML`)
2. **JSON** (`.ai-review.json` or path from `AI_REVIEW_CONFIG_FILE_JSON`)
3. **ENV** (`.env` or path from `AI_REVIEW_CONFIG_FILE_ENV`)
4. **Environment variables** (`LLM__PROVIDER=OPENAI`, etc.)
5. **Initialization arguments** (if used as a library)

---

## ⚙️ Override file paths

You can override default config locations using environment variables:

- `AI_REVIEW_CONFIG_FILE_YAML` — path to `.yaml` config
- `AI_REVIEW_CONFIG_FILE_JSON` — path to `.json` config
- `AI_REVIEW_CONFIG_FILE_ENV` — path to `.env`

By default, configs are loaded from the **project root**.

---

## 📘 Examples

- [.ai-review.yaml](./.ai-review.yaml) — main YAML config with comments
- [.ai-review.json](./.ai-review.json) — JSON config example
- [.env.example](./.env.example) — ENV config example

---

## 🔍 Tips

- Use **YAML** for most projects — it’s human-friendly and supports comments.
- **JSON** is convenient for automation (e.g., CI/CD pipelines).
- **ENV** is useful for local development and quick overrides.
