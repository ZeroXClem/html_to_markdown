import sys
import os
import logging

# Import the converter class from the previous file
# Make sure html_to_markdown_v2.py and markdown_rules_v2.py are in the same directory
# or accessible via Python's path.
try:
    from html_to_markdown_v2 import MarkdownConverter
except ImportError as e:
    print(f"Error: Could not import MarkdownConverter from html_to_markdown_v2.py.")
    print(f"Ensure html_to_markdown_v2.py and markdown_rules_v2.py are in the correct path.")
    print(f"Details: {e}")
    sys.exit(1)

# Configure basic logging for the interactive session
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# Create a converter instance (using default settings for simplicity)
# You could potentially add prompts here to customize ignore_tags or log level
try:
    converter = MarkdownConverter(log_level_str='INFO')
except Exception as e:
    logging.error(f"Failed to initialize MarkdownConverter: {e}", exc_info=True)
    sys.exit(1)

def get_html_from_file():
    """Prompts the user for a file path and reads the HTML content."""
    while True:
        try:
            input_file = input("Enter the path to the input HTML file: ").strip()
            if not input_file:
                print("Input file path cannot be empty.")
                continue
            with open(input_file, 'r', encoding='utf-8') as f:
                logging.info(f"Reading HTML from: {input_file}")
                return f.read()
        except FileNotFoundError:
            logging.error(f"Error: Input file not found at '{input_file}'. Please try again.")
        except IOError as e:
            logging.error(f"Error reading file '{input_file}': {e}")
            # Decide if you want to retry or exit here
            return None # Indicate failure
        except Exception as e:
            logging.error(f"An unexpected error occurred reading the file: {e}", exc_info=True)
            return None # Indicate failure

def get_html_from_paste():
    """Prompts the user to paste HTML content directly."""
    print("Paste your HTML content below.")
    print("Type '---ENDHTML---' on a new line and press Enter when done:")
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == '---ENDHTML---':
                break
            lines.append(line)
        except EOFError: # Handle Ctrl+D or similar EOF signals
            break
    logging.info("Received HTML content from paste.")
    return "\n".join(lines)

def save_markdown_to_file(markdown_content):
    """Prompts the user for an output file path and saves the Markdown."""
    while True:
        try:
            output_file = input("Enter the path for the output Markdown file: ").strip()
            if not output_file:
                print("Output file path cannot be empty.")
                continue

            # Check if file exists and ask for confirmation to overwrite
            if os.path.exists(output_file):
                confirm = input(f"File '{output_file}' already exists. Overwrite? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("Operation cancelled. Please choose a different file name.")
                    continue # Ask for output path again

            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                logging.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as out:
                logging.info(f"Writing Markdown to: {output_file}")
                out.write(markdown_content)
            print(f"Successfully saved Markdown to {output_file}")
            return True # Indicate success

        except IOError as e:
            logging.error(f"Error writing file '{output_file}': {e}")
            # Ask if they want to try again or cancel saving
            retry = input("Failed to save. Try a different path? (y/N): ").strip().lower()
            if retry != 'y':
                return False # Indicate cancellation
        except Exception as e:
            logging.error(f"An unexpected error occurred saving the file: {e}", exc_info=True)
            return False # Indicate failure

def interactive_main():
    """Runs the main interactive loop for HTML to Markdown conversion."""
    print("\n--- Interactive HTML to Markdown Converter ---")

    while True:
        print("\nSelect input method:")
        print("  1. Provide HTML file path")
        print("  2. Paste HTML content directly")
        print("  q. Quit")
        choice = input("Enter your choice (1, 2, or q): ").strip().lower()

        html_content = None
        if choice == '1':
            html_content = get_html_from_file()
            if html_content is None: # Handle read errors
                 continue # Go back to input method selection
        elif choice == '2':
            html_content = get_html_from_paste()
        elif choice == 'q':
            print("Exiting converter.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or q.")
            continue

        if not html_content or not html_content.strip():
             logging.warning("Received empty HTML content. Skipping conversion.")
             continue

        # --- Perform Conversion ---
        try:
            markdown_result = converter.convert(html_content)
        except ValueError as e: # Catch validation errors from converter
            logging.error(f"HTML Conversion Error: {e}")
            print("Could not convert the provided HTML. Please check the input.")
            continue
        except Exception as e:
            logging.error(f"An unexpected error occurred during conversion: {e}", exc_info=True)
            print("An unexpected error occurred. Please check the logs.")
            continue

        print("\n--- Conversion Successful ---")

        # --- Handle Output ---
        while True:
            print("\nSelect output method:")
            print("  1. Print Markdown to console")
            print("  2. Save Markdown to file")
            print("  c. Cancel output (convert new input)")
            output_choice = input("Enter your choice (1, 2, or c): ").strip().lower()

            if output_choice == '1':
                print("\n--- Markdown Output ---")
                print(markdown_result)
                print("--- End Markdown Output ---")
                break # Break output loop, go back to main input loop
            elif output_choice == '2':
                if save_markdown_to_file(markdown_result):
                    break # Break output loop (success), go back to main input loop
                else:
                    # save_markdown_to_file returned False (error or user cancel)
                    # Stay in the output selection loop
                    print("Returning to output options.")
                    continue
            elif output_choice == 'c':
                print("Output cancelled.")
                break # Break output loop, go back to main input loop
            else:
                print("Invalid choice. Please enter 1, 2, or c.")
                # Continue output selection loop

    # End of main while loop

if __name__ == "__main__":
    try:
        interactive_main()
    except KeyboardInterrupt:
        print("\nOperation interrupted by user. Exiting.")
        sys.exit(0)


