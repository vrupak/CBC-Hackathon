# Environment Variables Setup

## Required API Keys

Create a `.env` file in the **root directory** (project root, same level as `backend/` and `frontend/`) with the following API keys:

### 1. Supermemory API Key
```
SUPERMEMORY_API_KEY=your_supermemory_api_key_here
```

**How to get it:**
1. Sign up at [supermemory.ai](https://supermemory.ai)
2. Navigate to your account settings or API section
3. Generate a new API key
4. Copy the key and add it to your `.env` file

### 2. Anthropic (Claude) API Key
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**How to get it:**
1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Navigate to API Keys section
3. Create a new API key
4. Copy the key and add it to your `.env` file

### 3. Optional: Supermemory API URL
```
SUPERMEMORY_API_URL=https://api.supermemory.ai
```
(Defaults to the above if not specified. Do not include `/v1` in the URL)

## Example .env file

```env
# Supermemory API Configuration
SUPERMEMORY_API_KEY=sk-sm-your-supermemory-key-here
SUPERMEMORY_API_URL=https://api.supermemory.ai

# Anthropic (Claude) API Configuration
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
```

## Important Notes

1. **Never commit your `.env` file to git** - It's already in `.gitignore`
2. **Keep your API keys secure** - Don't share them publicly
3. **Test with minimal usage first** - Both services have usage-based pricing
4. **Check API quotas** - Make sure you have sufficient credits/quota

## Verification

After setting up your `.env` file in the root directory, you can verify the keys are loaded correctly by:

1. Starting the backend server (from `backend/` directory or root)
2. Checking the console for any API key errors
3. The server will start even if keys are missing (graceful degradation)
4. Upload a test file and check the response for `supermemory_ingested` and `topics_extracted` fields

**Note:** The `.env` file should be in the root directory of the project (same level as `backend/` and `frontend/` folders), not inside the `backend/` directory.


