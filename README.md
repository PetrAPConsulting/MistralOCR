# Mistral OCR Processing Tool

A versatile command-line tool for processing PDFs and images with Mistral's OCR API. This script extracts text content as markdown and preserves any embedded images.

## Features

- **Multi-format Support**: Process both PDF documents and image files (JPG, PNG, GIF, BMP, TIFF, WEBP)
- **Text Extraction**: Convert documents and images to clean markdown
- **Image Preservation**: Extract embedded images from documents if they are available in array
- **Batch Processing**: Process all supported files in a directory automatically
- **Structured Output**: Creates markdown files with the same name as the input files

## Requirements

- Python 3.6+
- `mistralai` Python package
- Mistral API key

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mistralocr.git
   cd mistralocr
   ```

2. Install the required dependencies:
   ```bash
   pip install mistralai
   ```

3. Set up your Mistral API key:
   - Option 1: Edit the script and replace `"your_api_key_here"` with your actual API key
   - Option 2: Set an environment variable:
     ```bash
     export MISTRAL_API_KEY="your_api_key_here"
     ```

## Usage

1. Place the script in a directory containing PDF and/or image files you want to process
2. Run the script:
   ```bash
   python mistral_ocr.py
   ```
3. The script will:
   - Find all supported files in the current directory
   - Process each file with the Mistral OCR API
   - Save extracted text as markdown files (`.md`)
   - Extract embedded images to `{filename}_images/` folders
   - Save full JSON responses as `{filename}_full.json` files

## Output Files

For each input file `example.pdf` or `example.jpg`, the script creates:

- `example.md`: The extracted text content in markdown format
- `example_full.json`: The complete JSON response from the Mistral OCR API
- `example_images/` (if images are found): A directory containing any extracted images

## How It Works

1. **File Detection**: The script scans the current directory for PDF and image files
2. **Upload**: Files are uploaded to Mistral's API
3. **OCR Processing**: The API extracts text and identifies any embedded images
4. **Content Extraction**: The script parses the API response to get markdown content
5. **Image Extraction**: Any embedded images are saved to a separate directory
6. **Output Generation**: Markdown files are created with references to the extracted images

## API Response Structure

The Mistral OCR API returns a JSON structure with the following key elements:

```json
{
  "pages": [
    {
      "index": 0,
      "markdown": "Extracted text in markdown format...",
      "images": [
        {
          "data": "base64 or URL data",
          "format": "png",
          "description": "Optional image description"
        }
      ],
      "dimensions": {"dpi": 200, "height": 5139, "width": 2387}
    }
  ],
  "model": "mistral-ocr-latest",
  "usage_info": {"pages_processed": 1, "doc_size_bytes": 199841}
}
```

## Limitations

- The script requires an active internet connection to access the Mistral API
- Processing large files may take time depending on your network speed
- The quality of text extraction depends on the clarity of the original documents
- API usage may be subject to rate limits or costs, depending on your Mistral account

## License

[MIT License](LICENSE)

## Acknowledgements

- This tool uses the [Mistral OCR API](https://docs.mistral.ai/capabilities/document/)
