# Console Interface for LLM Documentation Processing

## Overview

A unified console interface for building knowledge bases from PDF and Markdown documents, with improved rate limiting and debugging capabilities.

## Features

- ✅ **Interactive folder selection** - Choose input/output directories through console prompts
- ✅ **Rate limiter debugging** - Fixed typos, added retry limits, enhanced error handling  
- ✅ **System requirements check** - Automatically validates dependencies and API keys
- ✅ **Progress tracking** - Incremental processing with resume capability
- ✅ **Unified interface** - Single entry point for building and chatting

## Quick Start

### 1. Install Dependencies

```bash
pip install -r scripts/requirements.txt
```

### 2. Set up API Keys

Create a `.env` file in the project root:

```env
VOYAGE_API_KEY=your_voyage_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Run Console Interface

```bash
python console_interface.py
```

## Menu Options

### 1. Configure Input/Output Folders
- Set source folder containing `.pdf` and `.md` files
- Set destination folder for the knowledge database
- Automatic folder creation if needed

### 2. Build Knowledge Base
- Processes documents with improved rate limiting
- Handles PDF page-by-page chunking for legal citations
- Markdown section-based chunking
- **Rate Limiter Improvements**:
  - Fixed "timout" → "timeout" typo
  - Added max retry limit (5 attempts) 
  - Exponential backoff: 30s → 60s → 120s → 240s → 300s
  - Progress saved after each batch

### 3. Chat with Documents  
- Interactive chat interface using your knowledge base
- Vector search with reranking for accuracy
- Legal-focused prompting for precise responses

### 4. Rate Limiter Debug Info
- Current configuration details
- Recent improvements and fixes
- Troubleshooting tips for common issues

### 5. Check System Requirements
- Validate all package dependencies
- Verify API key configuration
- Environment setup verification

## Rate Limiting Improvements

### Before (Issues Fixed)
```python
# OLD: Typo prevented timeout detection
"timout" in error_msg

# OLD: Could retry infinitely  
return embed_batch_safe(client, batch_texts, model, retry_count + 1)
```

### After (Improvements)
```python
# NEW: Fixed typo and added retry limits
"timeout" in error_msg
if retry_count >= max_retries:
    print(f"Max retries ({max_retries}) exceeded. Giving up on this batch.")
    raise e
```

### Configuration
- **Batch Size**: 8 items per batch (conservative for rate limits)
- **RPM Delay**: 1 second between batches 
- **Max Retries**: 5 attempts per batch
- **Backoff Strategy**: Exponential with 5-minute cap
- **Error Detection**: Catches rate limit, 429, 500, 502, 503, timeout errors

## File Structure

```
llm-docs/
├── console_interface.py          # 🆕 Unified console interface  
├── test_implementation.py        # 🆕 Implementation verification
├── scripts/
│   ├── build_knowledge_v4.py     # ✅ Fixed rate limiter
│   ├── chat.py                   # ✅ Fixed DB path
│   └── requirements.txt          # ✅ Updated dependencies
├── chat.py                       # ✅ Fixed missing functions
└── docs-ai/                      # Knowledge database storage
```

## Troubleshooting

### Rate Limit Issues
- **Monthly quota exceeded**: Check usage at voyage.ai dashboard
- **Frequent 429 errors**: Reduce `BATCH_SIZE` in `build_knowledge_v4.py`  
- **Network timeouts**: Check internet connection, script will auto-retry

### Environment Issues
- **Missing API keys**: Verify `.env` file exists and has correct variable names
- **Import errors**: Install missing packages with `pip install package_name`
- **Database not found**: Build knowledge base before attempting to chat

### Common Error Messages
- `"Max retries exceeded"` → API service is down, try again later
- `"No knowledge base found"` → Run "Build Knowledge Base" first
- `"Build script not found"` → Ensure you're in the correct directory

## API Usage Guidelines

### VoyageAI Rate Limits
- Free tier: Limited requests per minute
- Paid tier: Higher limits but still rate limited
- The system automatically handles retries with exponential backoff

### Best Practices
1. Process documents in smaller batches during peak hours
2. Monitor your API usage dashboard  
3. Use the incremental processing feature to resume interrupted builds
4. Keep your API keys secure and don't commit them to version control

## Development Notes

The console interface provides a user-friendly wrapper around the existing processing scripts with these improvements:

- **Error resilience**: Better handling of API failures and network issues
- **User experience**: Clear prompts, progress indicators, and colored output
- **Debugging support**: Built-in diagnostics and troubleshooting guidance  
- **Flexibility**: Easy folder configuration without editing source code

For advanced users, the underlying scripts can still be called directly with command-line arguments.