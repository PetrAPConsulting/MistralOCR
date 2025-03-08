import os
import sys
import glob
import json
import base64
import urllib.request
from mistralai import Mistral

# Replace this with your actual API key
MISTRAL_API_KEY = "your_api_key_here"

def process_ocr_response(response_dict, base_name):
    """
    Process OCR response to extract markdown content and images
    
    Args:
        response_dict (dict): OCR response data
        base_name (str): Base filename for output
        
    Returns:
        str: Extracted markdown content
    """
    # Create a directory for images if any are found
    image_dir = f"{base_name}_images"
    has_images = False
    
    # Check if the response contains images - structure based on API documentation
    for page in response_dict.get('pages', []):
        if page.get('images') and len(page.get('images', [])) > 0:
            has_images = True
            break
            
    if has_images:
        os.makedirs(image_dir, exist_ok=True)
        print(f"  Created image directory: {image_dir}")
    
    # Process each page to extract markdown and handle images
    all_content = []
    
    for page_idx, page in enumerate(response_dict.get('pages', [])):
        page_markdown = page.get('markdown', '')
        page_images = page.get('images', [])
        
        # Process images in this page
        if page_images:
            print(f"  Found {len(page_images)} images on page {page_idx + 1}")
            
            # Create a dictionary to map image IDs to their base64 data
            image_data_dict = {}
            
            for img_idx, image in enumerate(page_images):
                # Get image ID and base64 data
                image_id = image.get('id')
                image_base64 = image.get('image_base64')
                
                if not image_id or not image_base64:
                    print(f"  Warning: Image {img_idx} is missing id or base64 data, skipping")
                    continue
                
                # Save the image to a file
                image_format = image.get('format', 'png')
                image_filename = f"{base_name}_page{page_idx + 1}_img{img_idx + 1}.{image_format}"
                image_path = os.path.join(image_dir, image_filename)
                
                try:
                    # Handle base64 data
                    if image_base64.startswith('data:image'):
                        # Extract the base64 string after the comma
                        b64_data = image_base64.split(',', 1)[1]
                    else:
                        # If it's already just the base64 data without prefix
                        b64_data = image_base64
                        
                    # Decode and save the image
                    with open(image_path, 'wb') as img_file:
                        img_file.write(base64.b64decode(b64_data))
                    print(f"  Saved image to {image_path}")
                    
                    # Add an entry to the dictionary mapping image ID to the local file path
                    # This will be used to replace the image references in the markdown
                    image_data_dict[image_id] = f"./{os.path.basename(image_dir)}/{image_filename}"
                    
                except Exception as e:
                    print(f"  Error saving image: {str(e)}")
            
            # Replace image references in the markdown
            for img_id, img_path in image_data_dict.items():
                # Format expected by the Mistral OCR API is ![id](id)
                page_markdown = page_markdown.replace(f"![{img_id}]({img_id})", f"![Image {img_id}]({img_path})")
        
        # Add processed page markdown to the content list
        all_content.append(page_markdown)
    
    # Join all pages with double newlines
    content = "\n\n".join(all_content)
    
    return content

def process_pdf_with_ocr(pdf_path):
    """
    Process a PDF file with Mistral's OCR API and save the results as a markdown file.
    
    Args:
        pdf_path (str): Path to the PDF file to process
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    # Get the file name without extension for the output file
    file_name = os.path.basename(pdf_path)
    base_name = os.path.splitext(file_name)[0]
    output_path = f"{base_name}.md"
    
    print(f"Processing '{file_name}'...")
    
    try:
        # Initialize the Mistral client
        client = Mistral(api_key=MISTRAL_API_KEY)
        
        # Step 1: Upload the PDF file
        print(f"  Uploading file...")
        uploaded_pdf = client.files.upload(
            file={
                "file_name": file_name,
                "content": open(pdf_path, "rb"),
            },
            purpose="ocr"
        )
        print(f"  File uploaded successfully. File ID: {uploaded_pdf.id}")
        
        # Step 2: Get a signed URL for the uploaded file
        print(f"  Getting signed URL...")
        signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
        print(f"  Signed URL obtained.")
        
        # Step 3: Process the file with OCR
        print(f"  Processing with OCR (this may take a while)...")
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": signed_url.url,
            },
            include_image_base64=True  # Enable base64 image extraction
        )
        
        # Convert the OCR response to a dictionary if it isn't already
        if hasattr(ocr_response, 'model_dump'):
            # For Pydantic models
            response_dict = ocr_response.model_dump()
        elif hasattr(ocr_response, 'dict'):
            # For older Pydantic models
            response_dict = ocr_response.dict()
        elif hasattr(ocr_response, 'to_dict'):
            # Some libraries use to_dict
            response_dict = ocr_response.to_dict()
        elif hasattr(ocr_response, '__dict__'):
            # Try the object's __dict__
            response_dict = ocr_response.__dict__
        else:
            # Try to convert the string representation to JSON
            try:
                response_dict = json.loads(str(ocr_response))
            except json.JSONDecodeError:
                # If it's not JSON, use the string representation
                response_dict = {"raw_text": str(ocr_response)}
        
        # Process the OCR response to extract content and images
        content = process_ocr_response(response_dict, base_name)
        
        # Save the extracted markdown content to a file
        print(f"  Saving extracted markdown content to {output_path}")
        with open(output_path, "w", encoding="utf-8") as md_file:
            md_file.write(content.strip())
            
        # Optionally save the full JSON response for reference
        json_output_path = f"{base_name}_full.json"
        with open(json_output_path, "w", encoding="utf-8") as json_file:
            json.dump(response_dict, json_file, indent=2)
        print(f"  Full OCR response saved to {json_output_path}")
        
        return True
        
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def process_image_with_ocr(image_path):
    """
    Process an image file with Mistral's OCR API and save the results as a markdown file.
    
    Args:
        image_path (str): Path to the image file to process
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    # Get the file name without extension for the output file
    file_name = os.path.basename(image_path)
    base_name = os.path.splitext(file_name)[0]
    output_path = f"{base_name}.md"
    
    print(f"Processing image '{file_name}'...")
    
    try:
        # Initialize the Mistral client
        client = Mistral(api_key=MISTRAL_API_KEY)
        
        # Step 1: Upload the image file
        print(f"  Uploading image...")
        uploaded_image = client.files.upload(
            file={
                "file_name": file_name,
                "content": open(image_path, "rb"),
            },
            purpose="ocr"
        )
        print(f"  Image uploaded successfully. File ID: {uploaded_image.id}")
        
        # Step 2: Get a signed URL for the uploaded image
        print(f"  Getting signed URL...")
        signed_url = client.files.get_signed_url(file_id=uploaded_image.id)
        print(f"  Signed URL obtained.")
        
        # Step 3: Process the image with OCR
        print(f"  Processing with OCR (this may take a while)...")
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "image_url",
                "image_url": signed_url.url,
            },
            include_image_base64=True  # Enable base64 image extraction
        )
        
        # Convert the OCR response to a dictionary
        if hasattr(ocr_response, 'model_dump'):
            response_dict = ocr_response.model_dump()
        elif hasattr(ocr_response, 'dict'):
            response_dict = ocr_response.dict()
        elif hasattr(ocr_response, 'to_dict'):
            response_dict = ocr_response.to_dict()
        elif hasattr(ocr_response, '__dict__'):
            response_dict = ocr_response.__dict__
        else:
            try:
                response_dict = json.loads(str(ocr_response))
            except json.JSONDecodeError:
                response_dict = {"raw_text": str(ocr_response)}
        
        # Process the OCR response to extract content and images
        content = process_ocr_response(response_dict, base_name)
        
        # Save the extracted markdown content to a file
        print(f"  Saving extracted markdown content to {output_path}")
        with open(output_path, "w", encoding="utf-8") as md_file:
            md_file.write(content.strip())
            
        # Optionally save the full JSON response for reference
        json_output_path = f"{base_name}_full.json"
        with open(json_output_path, "w", encoding="utf-8") as json_file:
            json.dump(response_dict, json_file, indent=2)
        print(f"  Full OCR response saved to {json_output_path}")
        
        return True
        
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def find_files_to_process():
    """
    Find all PDF and image files in the current directory.
    
    Returns:
        list: List of paths to files to process
    """
    # Define supported image file extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp']
    
    # Find all PDFs
    pdf_files = glob.glob("*.pdf")
    
    # Find all supported image files
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(f"*{ext}"))
        image_files.extend(glob.glob(f"*{ext.upper()}"))  # Also match uppercase extensions
    
    # Combine and return all files
    return pdf_files + image_files

def process_file(file_path):
    """
    Process a file with the appropriate OCR method based on file type
    
    Args:
        file_path (str): Path to the file to process
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    # Check file extension to determine processing method
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        return process_pdf_with_ocr(file_path)
    elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp']:
        return process_image_with_ocr(file_path)
    else:
        print(f"Unsupported file type: {file_extension}")
        return False

if __name__ == "__main__":
    # Find all eligible files in the current directory
    files = find_files_to_process()
    
    if not files:
        print("No PDF or image files found in the current directory.")
        sys.exit(1)
    
    print(f"Found {len(files)} file(s) to process.")
    
    # Process each file
    successful = 0
    failed = 0
    
    for file_path in files:
        if process_file(file_path):
            successful += 1
        else:
            failed += 1
    
    # Print summary
    print("\nProcessing complete!")
    print(f"Successfully processed: {successful}")
    print(f"Failed to process: {failed}")
