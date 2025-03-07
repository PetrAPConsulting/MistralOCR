import os
import sys
import glob
import json
import base64
import urllib.request
from mistralai import Mistral

# Replace this with your actual API key
MISTRAL_API_KEY = "mistral_api_key_here"

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
    
    # Check if the response contains images
    for page_idx, page in enumerate(response_dict.get('pages', [])):
        if page.get('images') and len(page.get('images', [])) > 0:
            has_images = True
            break
            
    if has_images:
        os.makedirs(image_dir, exist_ok=True)
        print(f"  Created image directory: {image_dir}")
    
    # Process each page to extract markdown and handle images
    content = ""
    for page_idx, page in enumerate(response_dict.get('pages', [])):
        page_markdown = page.get('markdown', '')
        page_images = page.get('images', [])
        
        # Process images in this page
        if page_images:
            print(f"  Found {len(page_images)} images on page {page_idx + 1}")
            
            for img_idx, image in enumerate(page_images):
                # Extract image data (assuming base64 encoded or URL)
                image_data = image.get('data')
                image_format = image.get('format', 'png')
                image_filename = f"{base_name}_page{page_idx + 1}_img{img_idx + 1}.{image_format}"
                image_path = os.path.join(image_dir, image_filename)
                
                # Save image if data is available
                if image_data:
                    if image_data.startswith('data:image'):
                        # Handle base64 encoded data
                        try:
                            # Extract the base64 string after the comma
                            b64_data = image_data.split(',', 1)[1]
                            with open(image_path, 'wb') as img_file:
                                img_file.write(base64.b64decode(b64_data))
                            print(f"  Saved image to {image_path}")
                        except Exception as e:
                            print(f"  Error saving image: {str(e)}")
                    elif image_data.startswith('http'):
                        # Handle image URL
                        try:
                            urllib.request.urlretrieve(image_data, image_path)
                            print(f"  Downloaded image from URL to {image_path}")
                        except Exception as e:
                            print(f"  Error downloading image: {str(e)}")
                    else:
                        print(f"  Unknown image data format, skipping")
                
                # Get image description if available
                image_description = image.get('description', '')
                if not image_description:
                    image_description = image.get('alt_text', '')
                if not image_description:
                    image_description = f"Image {img_idx + 1} on page {page_idx + 1}"
                
                # Create markdown reference to the image
                image_ref = f"\n\n![{image_description}](./{os.path.basename(image_dir)}/{image_filename})\n\n"
                
                # For now, just append the image reference at the end of the page content
                page_markdown += image_ref
        
        # Add page markdown to overall content
        content += page_markdown + "\n\n"
    
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
            }
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
            }
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
