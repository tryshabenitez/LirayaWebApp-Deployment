from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepInFrame, Preformatted
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader  
import os, tempfile
from uuid import uuid4
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
matplotlib.use("Agg")  
from io import BytesIO
from datetime import datetime, timedelta 
from reportlab.platypus import Table, TableStyle
from .models import *
from reportlab.platypus import Image
import requests


#----------------------------------- FORMAT AND STYLES-----------------------------------#

# Function to create the header (repeated on each page)
def create_header(canvas, doc):
    # Add Image from static folder (replace with your actual image path)
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images', 'liraya_pdficon.jpg')
    
    # Use ImageReader for better handling of PNG images (especially transparency)
    image = ImageReader(image_path)

    # Use ImageReader to draw the image (with transparency support) - is left + is right
    canvas.drawImage(image, 57, 683, width=1.38*inch, height=1.38*inch)  # Adjust image position and size
    
    # Define the text content
    text1 = "DEVELOPMENT OF KEYWORD-BASED SEARCH FOR"
    text2 = "TECHNOLOGICAL UNIVERSITY OF THE PHILIPPINES - CAVITE"
    text3 = "Technological University of the Philippines – Cavite"
    text4 = "Bachelor of Engineering Technology Major In Computer Engineering Technology"
    text5 = "Email: lirayaautomated@gmail.com | Website: www.tupcliraya.site"

    # Set font for the text
    canvas.setFont("Helvetica-Bold", 12)

    # Add the text next to the image - is left + is right
    canvas.drawString(155, 760, text1)  # Moved up from 740
    canvas.drawString(155, 745, text2)  # Moved up from 725

    # Set smaller font for additional details
    canvas.setFont("Helvetica", 10)
    canvas.drawString(155, 730, text3)  # Moved up from 710
    canvas.drawString(155, 715, text4)  # Moved up from 695
    canvas.drawString(155, 700, text5)  # Moved up from 
    
    # Add a thick line below the text
    canvas.setLineWidth(2)  # Set the thickness of the line (you can adjust this value)
    canvas.line(30, 689, 580, 689)  # Draw a line from x=40, y=690 to x=580, y=690 (horizontal line)

def create_footer(canvas, doc):
    """Function to create the footer in the PDF."""
    footer_text = "LIRAYA: Library Information Resource and Access\nCopyright © 2025, Technological University of the Philippines - Cavite"
    
    # Set font for the footer text
    canvas.setFont("Helvetica", 10)

    # Calculate the width of the page (letter size is 612 x 792)
    page_width = letter[0]
    
    # Split footer text into two lines
    lines = footer_text.split('\n')

    # Position for the first line (centered horizontally and placed near the bottom)
    canvas.drawString((page_width - canvas.stringWidth(lines[0], "Helvetica", 10)) / 2, 20, lines[0])

    # Position for the second line, just below the first line
    canvas.drawString((page_width - canvas.stringWidth(lines[1], "Helvetica", 10)) / 2, 20 + 12, lines[1])  # Adjust vertical position

def create_header_and_footer(canvas, doc):
    create_header(canvas, doc)
    create_footer(canvas, doc)
    
# Function to get header height
def get_header_height():
    return 110  # Adjust this based on the header's height (image + text)

# Function to get footer height
def get_footer_height():
    return 42  # Adjust footer height (reduce this value to bring text closer)

def create_table_with_split(table_data):
    """
    This function creates a table with splitByRow enabled to allow tables to break across multiple pages if needed.
    It also applies alternating row background colors, wraps content inside the cells, and handles content overflow.
    """
    # Define the table with column widths and enable row splitting across pages
    table = Table(table_data, colWidths=[1.8*inch, 4.6*inch], splitByRow=True)  # Allow table to split across pages if needed
    
    # Set the basic table style
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), '#451e23'),  # Header background color
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),  # Header text color
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Align text to the left for all cells
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # Set font size for all text
        ('BACKGROUND', (0, 1), (-1, -1), '#e8d8c4'),  # Row background color
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),  # Row text color
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Border color for the table
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),  # Padding for bottom of cells
        ('TOPPADDING', (0, 0), (-1, -1), 8),  # Padding for top of cells
        ('LEFTPADDING', (0, 0), (-1, -1), 8),  # Padding for left of cells
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),  # Padding for right of cells
        ('WORDWRAP', (0, 1), (-1, -1), True)  # Enable text wrapping for cells
    ]))
    
    # Alternating row background colors starting from row 2
    for row in range(1, len(table_data)):
        if row % 2 == 1:  # For odd rows (starting from row 2)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, row), (1, row), '#e8d8c4')  # Light color for odd rows
            ]))
        else:  # For even rows
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, row), (1, row), '#ffffff')  # White color for even rows
            ]))

    # Add content splitting functionality
    table._argW[0] = 1.8*inch  # Width of the first column
    table._argW[1] = 4.6*inch  # Width of the second column
    
    return table


# Function to create the user info table
def create_user_info_table_header(user_info):
    # Define styles for the table
    styles = getSampleStyleSheet()
    
    bold_style = ParagraphStyle(
        name='BoldStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10  # Set font size to 10
    )
    
    # Define normal style for wrapping text
    normal_style = styles['Normal']
    normal_style.wordWrap = 'CJK'  # Ensure word wrapping works well

    # Define custom style for table content
    table_content_style = ParagraphStyle(
        name='TableContentStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,  # Set font size specifically for table content
    )

    
    data = [
        [Paragraph(f"<b>Generated by:</b>", bold_style), Paragraph(f"{user_info['full_name']}", table_content_style)],
        [Paragraph(f"<b>Role:</b>", bold_style), Paragraph(f"{user_info['role']}", table_content_style)],
        [Paragraph(f"<b>Date Requested:</b>", bold_style), Paragraph(f"{user_info['date_generated']}", table_content_style)],
        [Paragraph(f"<b>Time Generated:</b>", bold_style), Paragraph(f"{user_info['time_generated']}", table_content_style)], 
    ]

    # Create the table with the data (2 columns and 2 rows)
    table = Table(data, colWidths=[2*inch, 4.5*inch], splitByRow=True)

    # Set the table style (background color, text alignment, padding)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), '#e8d8c4'),  # Set background color for all cells
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Align all text to the left
        ('TEXTCOLOR', (0, 0), (-1, -1), (0, 0, 0)),  # Set text color to black
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # Set font size for all text
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),  # Padding for bottom
        ('TOPPADDING', (0, 0), (-1, -1), 10),  # Padding for top
        ('LEFTPADDING', (0, 0), (-1, -1), 10),  # Left padding for cells
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),  # Right padding for cells
        ('GRID', (0, 0), (-1, -1), 5, (1, 1, 1))  # Set the border thickness to 1 and color to white
    ]))

    return table

def generate_pdf_format(output_pdf_path, file_name):
    #------------------------------- PAGE FORMAT -------------------------------#
    header_height = get_header_height()  # Adjust this based on the header's height (image + text)
    footer_height = get_footer_height()  # Adjust footer height (reduce this value to bring text closer)

    # Prepare the document
    document = SimpleDocTemplate(output_pdf_path, pagesize=letter, title=file_name)  # Set PDF title here
    flowables = []

    # Define custom heights for the header and footer space
    document.topMargin = header_height  # Space after header
    document.bottomMargin = footer_height  # Reduced space before footer

    #------------------------------- STYLES FORMAT -------------------------------#
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    style_normal.fontSize = 10  # Default font size

    # Title header style (for report titles)
    title_header_style = ParagraphStyle(
        name='TitleHeaderStyle',
        fontName='Helvetica-Bold',
        fontSize=35,  # Font size for title header
        alignment=1,  # Center alignment
        spaceAfter=20  # Space after the title
    )

    # Title topic style (for section titles)
    title_topic_style = ParagraphStyle(
        name='TitleTopicStyle',
        fontName='Helvetica-Bold',
        fontSize=15,  # Font size for topic titles
        alignment=0,  # Left alignment
        spaceAfter=10  # Space after the title
    )

    # Content style (for general text)
    content_style = styles['Normal']
    content_style.fontSize = 10  # Font size for contents
    content_style.leading = 12  # Line height for better readability

    # Table header style (for tables)
    tableheader_style = ParagraphStyle(
        name='HeaderStyle',
        fontName='Helvetica-Bold',
        fontSize=10,
        alignment=1,  # Centered
        textColor=colors.white,
    )

    # Table content style (for table content)
    titletable_style = ParagraphStyle(
        name='TitleTableStyle',
        fontName='Helvetica-Bold',
        fontSize=10,
        alignment=0,  # Left-aligned horizontally
        spaceBefore=6,  # Space before (padding to simulate top alignment)
        spaceAfter=6,   # Space after (padding to simulate bottom alignment)
    )

    # -------------------- 2ND HEADER TABLE STYLES --------------------#
    # Define the bold style for the labels
    bold_style = ParagraphStyle(
        name='BoldStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10  # Set font size to 10
    )

    # Define normal style for wrapping text (for name and other content)
    normal_style = styles['Normal']
    normal_style.wordWrap = 'CJK'  # Ensure word wrapping works well

    # Define custom style for table content with a fixed font size
    table_content_style = ParagraphStyle(
        name='TableContentStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10  # Set font size specifically for table content
    )

    return document, flowables, title_header_style, title_topic_style, content_style, tableheader_style, titletable_style, bold_style, normal_style, table_content_style




#----------------------------------- BOOK DETAILS (SPECIFIC) -----------------------------------#


def generate_book_details(output_pdf_path, dynamic_data=None, file_name="Unknown_Report.pdf", user_info=None):
    #------------------------------- PAGE FORMAT-------------------------------#
    header_height = get_header_height()  # Adjust this based on the header's height (image + text)
    footer_height = get_footer_height()  # Adjust footer height (reduce this value to bring text closer)
    # Prepare the document
    document = SimpleDocTemplate(output_pdf_path, pagesize=letter, title=file_name)  # Set PDF title here
    flowables = []
    # Define custom heights for the header and footer space
    document.topMargin = header_height  # Space after header
    document.bottomMargin = footer_height  # Reduced space before footer
    
    
    #------------------------------- STYLES FORMAT -------------------------------#
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    style_normal.fontSize = 10 
    
    title_header_style = ParagraphStyle(
        name='TitleHeaderStyle',
        fontName='Helvetica-Bold',  # Font style
        fontSize=35,  # Font size for title header
        alignment=1,  # Center alignment
        spaceAfter=20  # Space after the title
    )
    
    # Title topic style (24 font size)
    title_topic_style = ParagraphStyle(
        name='TitleTopicStyle',
        fontName='Helvetica-Bold',  # Font style
        fontSize=15,  # Font size for topic titles
        alignment=0,  # Center alignment
        spaceAfter=10  # Space after the title
    )
    
    # Content style (12 font size)
    content_style = styles['Normal']
    content_style.fontSize = 10  # Font size for contents
    content_style.leading = 12  # Line height for better readability
    
    # Style for the header (centered and bold)
    tableheader_style = ParagraphStyle(
        name='HeaderStyle',
        fontName='Helvetica-Bold',
        fontSize=10,
        alignment=1,  # Centered
        textColor=colors.white,
    )
    
    titletable_style = ParagraphStyle(
        name='TitleTableStyle',
        fontName='Helvetica-Bold',  # Bold text
        fontSize=10,  # Same font size
        alignment=0,  # Left-aligned horizontally
        spaceBefore=6,  # Space before (padding to simulate top alignment)
        spaceAfter=6,   # Space after (padding to simulate bottom alignment)
    )
    
    #------------------------------- 2nd Header -------------------------------#
    # Add title header directly with text and 35 font size
    title_header = "BOOK REPORT"  # Your header text here
    if title_header:
        title_header_paragraph = Paragraph(title_header, title_header_style)
        flowables.append(title_header_paragraph)
        flowables.append(Spacer(1, 12))  # Add space after title_header

    # Define user info for the table
    if user_info and dynamic_data:
        book_title = dynamic_data[0].get('title', 'Unknown Book Title')
        
        #-------------------- 2ND HEADER TABLE STYLES --------------------#
        # Define the bold style for the labels
        styles = getSampleStyleSheet()
        
        bold_style = ParagraphStyle(
            name='BoldStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10  # Set font size to 12
        )
        
        # Define normal style for wrapping text (for name and other content)
        normal_style = styles['Normal']
        normal_style.wordWrap = 'CJK'  # Ensure word wrapping works well
        
        
        # Define custom style for table content with a fixed font size
        table_content_style = ParagraphStyle(
            name='TableContentStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10  # Set font size specifically for table content
        )
        
        #-------------------- CONTENT --------------------#
        # Prepare data for the table (2 rows, 2 columns)
        data = [
            [Paragraph(f"<b>Generated by:</b>", bold_style), Paragraph(f"{user_info['full_name']}", table_content_style)],
            [Paragraph(f"<b>Role:</b>", bold_style), Paragraph(f"{user_info['role']}", table_content_style)],
            [Paragraph(f"<b>Date Requested:</b>", bold_style), Paragraph(f"{user_info['date_generated']}", table_content_style)],
            [Paragraph(f"<b>Time Generated:</b>", bold_style), Paragraph(f"{user_info['time_generated']}", table_content_style)],
            [Paragraph(f"<b>Book Title:</b>", bold_style), Paragraph(f"{book_title}", table_content_style)]  # Add book title here
        ]
        
        
        # Create the table with the data (2 columns and 2 rows)
        table = Table(data, colWidths=[2*inch, 4.5*inch], splitByRow=True)   # Adjust column widths to allow text wrapping
        
        # Set the table style (background color, text alignment, padding)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), '#e8d8c4'),  # Set background color for all cells
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Align all text to the left
            ('TEXTCOLOR', (0, 0), (-1, -1), (0, 0, 0)),  # Set text color to black
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),  # Set font size for all text
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),  # Padding for bottom
            ('TOPPADDING', (0, 0), (-1, -1), 10),  # Padding for top
            ('LEFTPADDING', (0, 0), (-1, -1), 10),  # Left padding for cells
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),  # Right padding for cells
            
            # Set border width and color for the table
            ('GRID', (0, 0), (-1, -1), 5, (1, 1, 1))  # Set the border thickness to 1 and color to white
        ]))
        
    
        # Add the table to flowables
        flowables.append(table)
        flowables.append(Spacer(1, 10))  
    
    
    #------------------------------- MAIN CONTENT -------------------------------#
    book_title = dynamic_data[0].get('title', 'Unknown Book Title')  # 
    title_topic1 = f"Figure 1: Total Views for {book_title}"
    if title_topic1:
        title_topic1_paragraph = Paragraph(title_topic1, title_topic_style)
        flowables.append(title_topic1_paragraph)
        flowables.append(Spacer(1, 5))  # Add space after title_topic1
        

    graph_path, graph_description = generate_book_view_graph(dynamic_data[0]['book_id'])
    
    if graph_path:
        try:
            # Check if the graph file exists
            if os.path.exists(graph_path):
                # Directly use Image for embedding the image in the PDF
                graph_image = Image(graph_path, width=6*inch, height=4*inch)
                flowables.append(graph_image)
                flowables.append(Spacer(1, 10))  # Space after the image
            else:
                print(f"Graph image not found: {graph_path}")
        except Exception as e:
            print(f"Error loading image: {e}")

    # Continue with the rest of the document generation...
    flowables.append(Paragraph(graph_description, content_style))
    flowables.append(Spacer(1, 10))

    flowables.append(Spacer(1, 20))  # Adding more space (20 units)
    # Add title topic1 directly with text and 24 font size
    title_topic2 = "Table 1. Book Details"
    if title_topic2:
        title_topic2_paragraph = Paragraph(title_topic2, title_topic_style)
        flowables.append(title_topic2_paragraph)
        flowables.append(Spacer(1, 5))  # Add space after title_topic1
            
    if dynamic_data:
        for data in dynamic_data:
            
            content_style.wordWrap = 'CJK'  # Ensure word wrapping works well
            scanned_content = data['scanned_content']  # Example plain text from the database
            if scanned_content:  # If content is not empty
                if '\n' in scanned_content or '\r' in scanned_content:  # Check if content has line breaks (preformatted)
                    # Use Preformatted to maintain the line breaks and spacing
                    scanned_content_paragraph = Preformatted(scanned_content, content_style)
                else:
                    # Use Paragraph for plain text content with word wrapping enabled
                    scanned_content_paragraph = Paragraph(scanned_content, content_style)
            
            
            # Prepare book details for table (2 columns)
            table_data = [
                [Paragraph("Label", tableheader_style), Paragraph("Description", tableheader_style)],  # Centered header
                [Paragraph("Uploaded by:", titletable_style), Paragraph(f"{data['uploaded_account_full_name']}", content_style)],
                [Paragraph("Date Uploaded:", titletable_style), Paragraph(f"{data['date_uploaded']}", content_style)],
                [Paragraph("Database ID:", titletable_style), Paragraph(f"{data['book_id']}", content_style)],
                [Paragraph("Title:", titletable_style), Paragraph(f"{data['title']}", content_style)],
                [Paragraph("Book Type:", titletable_style), Paragraph(f"{data['book_type']}", content_style)],  
                [Paragraph("Scanned Type:", titletable_style), Paragraph(f"{data['scanned_type']}", content_style)],
                [Paragraph("Author:", titletable_style), Paragraph(f"{data['author']}", content_style)],
                [Paragraph("Co-Author:", titletable_style), Paragraph(f"{data['co_author']}", content_style)],
                [Paragraph("Year of Publication:", titletable_style), Paragraph(f"{data['year_of_publication']}", content_style)],
                [Paragraph("Publisher:", titletable_style), Paragraph(f"{data['publisher']}", content_style)],
                [Paragraph("Shelf Category:", titletable_style), Paragraph(f"{data['shelf_category']}", content_style)],
            ]
            
            # Create a table for book details
            table = create_table_with_split(table_data)   # Adjust column widths     
            # Add the table to flowables
            flowables.append(table)
            flowables.append(Spacer(1, 10))  # Space after the table

            primary_keyword = data.get('primary_keyword') or ""
            if primary_keyword:
                flowables.append(Paragraph("Primary Keywords", title_topic_style))
                
                dashed_line = "--------------------------------------------"  # String of dashes
                dashed_line *= 3 
                
                flowables.append(Paragraph(dashed_line, content_style))
                flowables.append(Spacer(1, 10))
                
                # preserve line breaks
                flowables.append(Paragraph(primary_keyword.replace("\n", "<br/>"), content_style))
                flowables.append(Spacer(1, 10))
            
            scanned_content = data.get('scanned_content') or ""
            if scanned_content:
                flowables.append(Paragraph("Scanned Content", title_topic_style))
                
                dashed_line = "--------------------------------------------"  # String of dashes
                dashed_line *= 3 
                
                flowables.append(Paragraph(dashed_line, content_style))
                flowables.append(Spacer(1, 10))
                
                # preserve line breaks
                flowables.append(Paragraph(scanned_content.replace("\n", "<br/>"), content_style))
                flowables.append(Spacer(1, 10))
        #------------------------------- MAIN CONTENT-------------------------------#
    # Build the document with flowables and both header/footer on every page
    document.build(flowables, onFirstPage=create_header_and_footer, onLaterPages=create_header_and_footer)
    
    if os.path.exists(graph_path):
        os.remove(graph_path)  # Remove the temporary graph file
    

def generate_book_view_graph(book_id):
    # Fetch the BookViewLog data for the given book_id
    view_log = BookViewLog.objects.filter(book_id=book_id)
    
    # Fetch the book title (assuming you have access to the book title in your model)
    book = Books.objects.get(book_id=book_id)
    title = book.title  # Assuming 'title' is a field in your Book model

    # If no data exists, still show the graph but with a message
    if not view_log.exists():
        # Fetch the maximum count of views among all books to set as data range
        max_count = BookViewLog.objects.aggregate(max_count=models.Max('book_count'))['max_count']
        
        # If there are no logs in the entire system, use a default value
        if max_count is None:
            max_count = 1  # Default value to avoid plotting issues

        # Set a dummy data set to create a plot
        dummy_counts = [0]  # Set the actual counts to zero for the book with no data
        dummy_title = title # Title for books with no data

        # Create the plot with the maximum count and a dummy title
        fig, ax = plt.subplots(figsize=(8, 6))
        bars = ax.bar([dummy_title] * len(dummy_counts), dummy_counts, color='#451e23', edgecolor='black', linewidth=1.5)

        # Set the y-axis range to the maximum count across all books
        ax.set_ylim(0, max_count)

        # Round the top corners of the bars
        for bar in bars:
            bar.set_capstyle('round')  # Round the top corners

        ax.set_ylabel('View Count')
        ax.set_xlabel('Book')
        ax.set_title(f"Total Views: 0")

        # Save the graph in the 'graphs' directory under MEDIA_ROOT
        media_dir = os.path.join(os.getcwd(), 'LirayaApp', 'media', 'graphs')
        if not os.path.exists(media_dir):
            os.makedirs(media_dir)  # Create the directory if it doesn't exist
        
        graph_filename = f"book_view_graph_{book_id}_no_data.png"
        graph_path = os.path.join(media_dir, graph_filename)
        
        # Save the plot to the file
        plt.tight_layout()
        plt.savefig(graph_path)
        plt.close()

        # Create a description for the graph
        graph_description = f"Figure 1: No data available for book: {title}. This book has not been opened yet, so no view data is available.<br/><br/><br/>"

        # Return the graph path and description
        return graph_path, graph_description
    
        # Extract data for plotting
    dates = [log.created_at for log in view_log]
    latest_date = [log.updated_at for log in view_log]
    counts = [log.book_count for log in view_log]
    date_today = datetime.today()

    # Ensure there is data to process
    if dates and latest_date:  # Check if the lists aren't empty
        # Directly use the first date and the last date from the lists
        start_date = dates[0]  # First date (the earliest in the list)
        end_date = latest_date[-1]  # Last date (the most recent in the list)
        # Calculate the period in days (avoid division by zero)
        period_days = (end_date - start_date).days or 1  # Avoid division by zero
        # Calculate total views (if you want to use sum or just counts, you can adjust here)
        total_views = sum(counts)  # If you want the total views, sum the counts
        # Calculate average views per day
        average_views_per_day = total_views / period_days

    else:
        # Handle the case where there is no data available
        print("Hello - No data available")
        start_date = end_date = None
        period_days = 0
        total_views = 0
        average_views_per_day = 0
    
    # Plotting the bar graph
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar([title] * len(counts), counts, color='#451e23', edgecolor='black', linewidth=1.5)
    
    # Round top corners of the bars
    for bar in bars:
        bar.set_capstyle('round')  # Round the top corners

    all_counts = [log.book_count for log in BookViewLog.objects.all()]  

    # Find the maximum book_count across all view_log entries
    max_count = max(all_counts) if all_counts else 1
    

    # Add a small buffer to the max count (e.g., 5 or 10) for a cleaner visualization
    buffer = 11  # You can change this value to 5 or any other number if you prefer
    ax.set_ylim(0, max_count + buffer)  # Set the range from 0 to max_count + buffer
    
    ax.set_ylabel('View Count')
    ax.set_xlabel('Book')
    ax.set_title(f"Total Views: {total_views} ")
    
    # Rotate the date labels for better visibility
    plt.xticks(rotation=0)
    
    # Save the graph in the 'graphs' directory under MEDIA_ROOT
    media_dir = os.path.join(os.getcwd(), 'LirayaApp', 'media', 'graphs')
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)  # Create the directory if it doesn't exist
    
    graph_filename = f"book_view_graph_{book_id}.png"
    graph_path = os.path.join(media_dir, graph_filename)
    
    # Save the plot to the file
    plt.tight_layout()
    plt.savefig(graph_path)
    plt.close()
    
    # Create a description for the graph
    graph_description = (f"Figure 1: Bar graph represents the total views for the book. "
                     f"The data shown covers the period from <b>{start_date.strftime('%B %d, %Y')}</b> "
                     f"to <b>{date_today.strftime('%B %d, %Y')}</b>, with a total of <b>{total_views}</b> views "
                     f"during this period. The average views per day for this book during this period "
                     f"is <b>{average_views_per_day:.2f}</b>. This shows that, on average, the book received "
                     f"<b>{average_views_per_day:.2f}</b> views per day throughout the  <b>{period_days}</b> day(s) period.")
    
    # Return the graph path and description
    return graph_path, graph_description


#----------------------------------- ALL BOOKS RECORDS -----------------------------------#
# Generate Account Book Records Report
def generate_account_bookrecords(pdf_buffer, account_info_data, categorized_books_data, user_info, file_name, graph_path=None, graph_description=None, all_description_of_tables_data=None, shelf_counts_data=None, start_date_str=None, end_date_str=None):
    # Use the reusable page format and 
    flowables = []
    document, flowables, title_header_style, title_topic_style, content_style, tableheader_style, titletable_style, bold_style, normal_style, table_content_style = generate_pdf_format(pdf_buffer, "Liraya_AccountBookRecords_Report")
    # Add Title for Report
    title_header_style = ParagraphStyle(
        name='TitleHeaderStyle',
        fontName='Helvetica-Bold',  # Font style
        fontSize=30,  # Font size for title header
        alignment=1,  # Center alignment
        spaceAfter=20  # Space after the title
    )
    
    semi_title_header_style = ParagraphStyle(
        name='TitleHeaderStyle',
        fontName='Helvetica-Bold',  # Font style
        fontSize=20,  # Font size for title header
        alignment=1,  # Center alignment
        spaceAfter=15  # Space after the title
    )
    
    daterange_header_style = ParagraphStyle(
        name='DateRangeHeaderStyle',
        fontName='Helvetica',  # Font style
        fontSize=12,  # Font size for title header
        alignment=1,  # Center alignment
        spaceAfter=15  # Space after the title
    )

    # safely extract range from the payload (supports both 'date_range' and 'data_range')
    range_code = next(
        ((row.get('date_range') or row.get('data_range'))
         for row in account_info_data
         if isinstance(row, dict) and ('date_range' in row or 'data_range' in row)),
        'all_time'   # fallback if list is empty / missing key
    )

    RANGE_LABELS = {
        'today': 'Today',
        'last_1_week': 'Last 1 Week',
        'last_2_weeks': 'Last 2 Weeks',
        'last_1_month': 'Last 1 Month',
        'last_6_months': 'Last 6 Months',
        'last_1_year': 'Last 1 Year',
        'all_time': 'All Time',
    }
    
    data_range_label = RANGE_LABELS.get(range_code, str(range_code))
    
    title_header = Paragraph("Account Book Records Report", title_header_style)
    flowables.append(title_header)
    flowables.append(Spacer(1, 12))  # Space after the title
    
    flowables.append(Paragraph(f"Book Range: {data_range_label}", semi_title_header_style))
    flowables.append(Spacer(1, 12))

    # Show one date if start == end; otherwise show the range. Also handle single/missing values.
    if start_date_str and end_date_str:
        if start_date_str == end_date_str:
            flowables.append(Paragraph(f"({start_date_str})", daterange_header_style))
        else:
            flowables.append(Paragraph(f"({start_date_str} to {end_date_str})", daterange_header_style))
        flowables.append(Spacer(1, 12))
    elif start_date_str or end_date_str:
        single = start_date_str or end_date_str
        flowables.append(Paragraph(f"({single})", daterange_header_style))
        flowables.append(Spacer(1, 12))

    # Call create_user_info_table to generate the user info table
    user_info_table = create_user_info_table_header(user_info)
    flowables.append(user_info_table)
    flowables.append(Spacer(1, 12))  # Add space after the user info table

    # ------------------- Librarian Table ------------------------ #
    title_topic1 = "Table 1. Librarians/Departments and Their Book Uploads Overview"
    title_topic1_paragraph = Paragraph(title_topic1, title_topic_style)
    flowables.append(title_topic1_paragraph)
    flowables.append(Spacer(1, 5))  # Add space after title_topic1
    
    table_data = [
        [Paragraph('No.', tableheader_style), 
         Paragraph('Full Name / Role', tableheader_style), 
         Paragraph('Books Uploaded', tableheader_style), 
         Paragraph('Latest Upload Date', tableheader_style)]
    ]

    for index, librarian in enumerate(account_info_data):  
        table_data.append([
            Paragraph(str(index + 1), table_content_style),
            Paragraph(f"{librarian.get('account_name', 'N/A')} (" 
                      f"{librarian.get('role', 'N/A')})", table_content_style),
            Paragraph(str(librarian['total_books_uploaded']), table_content_style),
            Paragraph(str(librarian['latest_book_date']), table_content_style)
        ])
    
    table = Table(table_data, colWidths=[0.5*inch, 3.1*inch, 1.3*inch, 1.5*inch], splitByRow=True)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (3, 0), '#451e23'),
        ('TEXTCOLOR', (0, 0), (3, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), '#f0f0f0'),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('WORDWRAP', (0, 1), (-1, -1), True),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
    ]))

    for row in range(1, len(table_data)):
        if row % 2 == 1:
            table.setStyle(TableStyle([('BACKGROUND', (0, row), (4, row), '#e8d8c4')]))
        else:
            table.setStyle(TableStyle([('BACKGROUND', (0, row), (4, row), '#ffffff')]))

    flowables.append(table)
    flowables.append(Spacer(1, 12))

    description_paragraph_table1 = Paragraph(all_description_of_tables_data[0]['account_info_desc'], content_style)  # Create paragraph for the description
    flowables.append(description_paragraph_table1)  # Add it to flowables
    flowables.append(Spacer(1, 12)) 
    
    title_figure1 = "Figure 1: Librarian/Department Book Uploads Over Time"
    title_figure1_paragraph = Paragraph(title_figure1, title_topic_style)
    flowables.append(title_figure1_paragraph)
    flowables.append(Spacer(1, 5))  # Add space after title_topic2
    
    if graph_path:
        graph_image = Image(graph_path, width=6*inch, height=4*inch)
        flowables.append(graph_image)
        flowables.append(Spacer(1, 10))  # Space after the image
        
        if graph_description:
            description_paragraph = Paragraph(graph_description, content_style)
            flowables.append(description_paragraph)
            flowables.append(Spacer(1, 10))  # Space after the description

    
    # ------------------- Categorized Books Table ------------------------ #

    # Thesis Books Table
    title_topic2 = "Table 2. Thesis Books Catalogue"
    title_topic2_paragraph = Paragraph(title_topic2, title_topic_style)
    flowables.append(title_topic2_paragraph)
    flowables.append(Spacer(1, 5))  # Add space after title_topic2

    # Prepare table data for Thesis books
    
    table_data = [
        [Paragraph('No.', tableheader_style), 
         Paragraph('Title', tableheader_style), 
         Paragraph('Author(s)', tableheader_style), 
         Paragraph('Date Uploaded', tableheader_style),
         Paragraph('Views', tableheader_style),] 
    ]
    

    thesis_books_data = [category for category in categorized_books_data if category['book_type'] == 'Thesis']
    
    if thesis_books_data:
        # Loop through the Thesis books and add data to the table
        for index, category in enumerate(thesis_books_data, 1):  # Start numbering from 1
            table_data.append([
                Paragraph(str(index), table_content_style),  # Numbering starts from 1 and increments
                Paragraph(category['title'], table_content_style),
                Paragraph(category['author'], table_content_style),
                Paragraph(str(category['date_uploaded']), table_content_style),
                Paragraph(str(category['book_count']), table_content_style)  # Book views count
            ])
    else:
        # If no thesis books, add "No Data"
        table_data.append([Paragraph('N/A', table_content_style), Paragraph('No Data', table_content_style), 
                           Paragraph('No Data', table_content_style), Paragraph('N/A', table_content_style), Paragraph('0', table_content_style)])

    # Create the Thesis books table
    thesis_books_table = Table(table_data, colWidths=[0.5*inch, 2.8*inch, 1.3*inch, 1.2*inch, 0.6*inch, 0.9*inch])
    thesis_books_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#451e23'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), '#ffffff'),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('WORDWRAP', (0, 1), (-1, -1), True),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
    ]))
    
    # Apply alternating row background colors (skip the header row)
    for row in range(1, len(table_data)):  # Start from row 1 (skip the header row)
        if row % 2 == 1:  # For odd rows (starting from row 2)
            thesis_books_table.setStyle(TableStyle([('BACKGROUND', (0, row), (-1, row), '#e8d8c4')]))  # Light color for odd rows
        else:  # For even rows
            thesis_books_table.setStyle(TableStyle([('BACKGROUND', (0, row), (-1, row), '#ffffff')]))  # White color for even rows
                
    flowables.append(thesis_books_table)
    flowables.append(Spacer(1, 12))
    
    description_paragraph_table1 = Paragraph(all_description_of_tables_data[1]['thesis_books_desc'], content_style)  # Create paragraph for the description
    flowables.append(description_paragraph_table1)  # Add it to flowables
    flowables.append(Spacer(1, 12)) 
    
    # Academic Books Table
    title_topic3 = "Table 3. Academic Books Catalogue"
    title_topic3_paragraph = Paragraph(title_topic3, title_topic_style)
    flowables.append(title_topic3_paragraph)
    flowables.append(Spacer(1, 5))  # Add space after title_topic3

    # Prepare table data for Academic books
    table_data = [
        [Paragraph('No.', tableheader_style), 
         Paragraph('Title', tableheader_style), 
         Paragraph('Author(s)', tableheader_style), 
         Paragraph('Date Uploaded', tableheader_style),
         Paragraph('Views', tableheader_style),] 
    ]

    academic_books_data = [category for category in categorized_books_data if category['book_type'] == 'Academic']
    
    if academic_books_data:
        # Loop through the Academic books and add data to the table
        for index, category in enumerate(academic_books_data, 1):  # Start numbering from 1
            table_data.append([
                Paragraph(str(index), table_content_style),  # Numbering starts from 1 and increments
                Paragraph(category['title'], table_content_style),
                Paragraph(category['author'], table_content_style),
                Paragraph(str(category['date_uploaded']), table_content_style),
                Paragraph(str(category['book_count']), table_content_style)  # Book views count
            ])
    else:
        # If no academic books, add "No Data"
        table_data.append([Paragraph('N/A', table_content_style), Paragraph('No Data', table_content_style), 
                           Paragraph('No Data', table_content_style), Paragraph('N/A', table_content_style), Paragraph('0', table_content_style)])

    # Create the Academic books table
    academic_books_table = Table(table_data, colWidths=[0.5*inch, 2.8*inch, 1.3*inch, 1.2*inch, 0.6*inch, 0.9*inch])
    academic_books_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#451e23'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), '#ffffff'),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('WORDWRAP', (0, 1), (-1, -1), True),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
    ]))
    
    for row in range(1, len(table_data)):  # Start from row 1 (skip the header row)
        if row % 2 == 1:  # For odd rows (starting from row 2)
            academic_books_table.setStyle(TableStyle([('BACKGROUND', (0, row), (-1, row), '#e8d8c4')]))  # Light color for odd rows
        else:  # For even rows
            academic_books_table.setStyle(TableStyle([('BACKGROUND', (0, row), (-1, row), '#ffffff')]))  # White color for even rows

    flowables.append(academic_books_table)
    flowables.append(Spacer(1, 12))
    

    description_paragraph_table1 = Paragraph(all_description_of_tables_data[2]['academic_books_desc'], content_style)  # Create paragraph for the description
    flowables.append(description_paragraph_table1)  # Add it to flowables
    flowables.append(Spacer(1, 12)) 
    
    
    # Thesis Books Table
    title_topic4 = "Table 4. Shelf Books Count by Category"
    title_topic4_paragraph = Paragraph(title_topic4, title_topic_style)
    flowables.append(title_topic4_paragraph)
    flowables.append(Spacer(1, 5))  # Add space after title_topic4

    # Shelf Category table (2 columns: Shelf Category, Count)
    shelf_table_data = [
        [Paragraph('Shelf Category', tableheader_style), Paragraph('Count', tableheader_style)]
    ]

    if shelf_counts_data:
        for row in shelf_counts_data:
            shelf_table_data.append([
                Paragraph(str(row.get('shelf_category') or 'Uncategorized'), table_content_style),
                Paragraph(str(row.get('count') or 0), table_content_style),
            ])
    else:
        shelf_table_data.append([
            Paragraph('N/A', table_content_style),
            Paragraph('0', table_content_style),
        ])

    shelf_table = Table(shelf_table_data, colWidths=[4.8*inch, 1.6*inch])
    shelf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#451e23'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), '#ffffff'),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('WORDWRAP', (0, 1), (-1, -1), True),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
    ]))

    for row_idx in range(1, len(shelf_table_data)):
        if row_idx % 2 == 1:
            shelf_table.setStyle(TableStyle([('BACKGROUND', (0, row_idx), (-1, row_idx), '#e8d8c4')]))
        else:
            shelf_table.setStyle(TableStyle([('BACKGROUND', (0, row_idx), (-1, row_idx), '#ffffff')]))

    flowables.append(shelf_table)
    flowables.append(Spacer(1, 12))

    # Shelf table description (index 3)
    if all_description_of_tables_data and len(all_description_of_tables_data) >= 4:
        shelf_desc_html = all_description_of_tables_data[3].get('shelf_counts_desc')
        if shelf_desc_html:
            flowables.append(Paragraph(shelf_desc_html, content_style))
            flowables.append(Spacer(1, 12))

    # Build the document
    document.build(flowables, onFirstPage=create_header_and_footer, onLaterPages=create_header_and_footer)







#----------------------------------- ACCOUNT INFORMATION -----------------------------------#

# account information 
def _style_sheet():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallBlack", fontSize=10, textColor=colors.black, leading=13))
    styles.add(ParagraphStyle(name="SmallGray", fontSize=9, textColor=colors.gray, leading=12))
    styles.add(ParagraphStyle(name="BannerTitle", fontSize=16, leading=18, alignment=1))  # centered
    styles.add(ParagraphStyle(name="BannerSub", fontSize=10, leading=12, alignment=1, textColor=colors.gray))
    styles.add(ParagraphStyle(name="SectionTitle", fontSize=15, leading=14, spaceBefore=9, spaceAfter=9, fontName="Helvetica-Bold" ))
    styles.add(ParagraphStyle(name="Cell", fontSize=10, leading=12, wordWrap='CJK'))  # wraps long values like address
    styles.add(ParagraphStyle(name="CellLabel", fontSize=10, textColor=colors.gray, leading=12))
    styles.add(ParagraphStyle(name="Strong", fontSize=10, leading=12))
    styles.add(ParagraphStyle(
        name="BannerTitleWhite",
        parent=styles["BannerTitle"],
        fontName="Helvetica-Bold",
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name="CellNoWrap",
        parent=styles["Cell"],
        wordWrap=None,           # disable wrapping
        splitLongWords=False,
    ))
    styles.add(ParagraphStyle(
    name="SectionTitleCenter",
    parent=styles["SectionTitle"],   # inherits bold / spacing
    alignment=1                      # 1 = TA_CENTER
    ))
    styles.add(ParagraphStyle(name="BannerSubWhite",parent=styles["BannerSub"],textColor=colors.white))
    return styles

MAROON = colors.Color(0.294, 0.055, 0.055)        # same deep maroon
ROSE   = colors.HexColor("#f3e9e9")   

DEFAULT_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "static", "images", "default_profile-picture.png")

def _placeholder_box(width, height, text="No Photo"):
    """Used if even the default image file can't be loaded."""
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#f1f1f1"),
               strokeColor=MAROON, strokeWidth=0.8))
    d.add(String(width/2, height/2, text, textAnchor="middle",
                 fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#666666")))
    return d

def _fetch_image_from_url(url, width=1.0*inch, height=1.0*inch):
    """
    Fetch image from a URL or base64 string.
    If missing or invalid, fall back to static 'default_profile-picture.png'.
    Always returns a ReportLab flowable.
    """
    # Case 1: No image URL provided → use default
    if not url:
        try:
            return Image(DEFAULT_IMAGE_PATH, width, height)
        except Exception:
            return _placeholder_box(width, height)

    # Case 2: Handle base64-encoded image (data:image/png;base64,...)
    if isinstance(url, str) and url.startswith("data:image"):
        try:
            header, b64data = url.split(",", 1)
            img_data = BytesIO(base64.b64decode(b64data))
            return Image(img_data, width, height)
        except Exception:
            try:
                return Image(DEFAULT_IMAGE_PATH, width, height)
            except Exception:
                return _placeholder_box(width, height)

    # Case 3: Normal image URL
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        img_data = BytesIO(resp.content)
        return Image(img_data, width, height)
    except Exception:
        try:
            return Image(DEFAULT_IMAGE_PATH, width, height)
        except Exception:
            return _placeholder_box(width, height)

def _center_banner(meta, styles):
    """Maroon title bar (white text), gray subtitle, and a borderless one-line meta row."""
    title = meta.get("title", "Account Information Report")
    rng   = (meta.get("range_label") or "the selected range")
    by    = meta.get("generated_by", "—")
    role  = (meta.get("generated_by_role") or "").strip()

    # Humanized scope like the KPI summary
    rng_lower = str(rng).strip().lower()
    scope_text = "the whole period of using the system" if rng_lower == "all time" else rng

    pieces = []

    # --- Title on maroon bar (white, centered)
    title_tbl = Table(
        [[Paragraph(title, styles["BannerTitleWhite"])]],
        colWidths=[6.7*inch]   # match your page content width
    )
    title_tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,-1), MAROON),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('LEFTPADDING',  (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING',   (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
    ]))
    pieces.append(title_tbl)

    # --- Subtitle (gray, no background)
    sub_para = Paragraph(
        f"Detailed account information and performance within {scope_text}.",
        styles["BannerSubWhite"]
    )
    sub_tbl = Table([[sub_para]], colWidths=[6.7*inch])
    sub_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), MAROON),
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ('LEFTPADDING',  (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING',   (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]))
    pieces.append(sub_tbl)
    pieces.append(Spacer(1, 8))

    # --- One-line meta row (left: Report Coverage | right: Generated by)
    by_text    = f"{by} ({role})" if role else by
    right_para = Paragraph(f"<b>Generated by:</b> {by_text}", styles["CellNoWrap"])

    # Keep on one line; shrink slightly if it would wrap
    right_box = KeepInFrame(
        maxWidth=6.7*inch,  # full content width
        maxHeight=14,
        content=[right_para],
        mode="shrink"
    )

    meta_row = Table([[right_box]], colWidths=[6.7*inch])
    meta_row.setStyle(TableStyle([
        ('ALIGN',        (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING',   (0,0), (-1,-1), 2),
        ('BOTTOMPADDING',(0,0), (-1,-1), 2),
    ]))
    pieces.append(meta_row)
    pieces.append(Spacer(1, 10))
    return pieces


def _info_rows(bio):
    data = [
        ["Role:", bio.get("role","—")],
        ["Full Name:", bio.get("full_name","—")],
        ["Username:", bio.get("username","—")],
    ]
    tbl = Table(data, colWidths=[1.2*inch, 3.0*inch])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('GRID',       (0,0), (-1,-1), 0.6, MAROON),
        ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    return tbl

def _personal_info_table(bio, styles):
    ROSE = colors.HexColor("#f6d7d7")  # same pink used above

    P = lambda text: Paragraph(str(text), styles["Cell"])
    L = lambda text: Paragraph(f"<b>{text}</b>", styles["Cell"])

    data = [
    [L("Birthday:"),           P(_format_date_words(bio.get("birth_date")))],
    [
        L("Age:"),
        P(
            "—"
            if not bio.get("age_years")
            else f"{bio['age_years']} year{'s' if int(bio['age_years']) != 1 else ''} old"
        ),
    ],

    [L("Email:"),              P(bio.get("email","—"))],
    [L("Contact Number:"),     P(bio.get("contact","—"))],
    [L("Gender:"),             P(bio.get("gender","—"))],
    [L("Created by:"),         P(bio.get("created_by","—"))],
    [L("Address:"),            P(bio.get("address","—"))],
    [L("City/Municipality:"),  P(bio.get("city","—"))],
    [L("Province:"),           P(bio.get("province","—"))],
    [L("State:"),              P(bio.get("state","—"))],
    [L("Zipcode:"),            P(bio.get("zipcode","—"))],
]
    #               Label         Value     (sum = 6.7")
    t = Table(data, colWidths=[1.8*inch, 3.8*inch])
    t.setStyle(TableStyle([
        # maroon borders everywhere
        ('GRID', (0,0), (-1,-1), 0.6, MAROON),
        ('BOX',  (0,0), (-1,-1), 0.8, MAROON),

        # pink label column, black text
        ('BACKGROUND', (0,0), (0,-1), ROSE),
        ('TEXTCOLOR',  (0,0), (0,-1), colors.black),
        ('FONT',       (0,0), (0,-1), 'Helvetica-Bold', 10),

        # white value column, black text
        ('BACKGROUND', (1,0), (1,-1), colors.white),
        ('TEXTCOLOR',  (1,0), (1,-1), colors.black),
        ('FONT',       (1,0), (1,-1), 'Helvetica', 10),

        # padding
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING',   (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]))
    return t

def _format_date_words(date_value):
    """Convert YYYY-MM-DD or datetime to 'Month Day, Year'."""
    if not date_value:
        return "—"
    if isinstance(date_value, str):
        try:
            dt = datetime.strptime(date_value, "%Y-%m-%d")
        except ValueError:
            return date_value
    else:
        dt = date_value
    return dt.strftime("%B %d, %Y")

def _parse_any_date(s):
    """Parse 'YYYY-MM-DD' or ISO 'YYYY-MM-DDTHH:MM:SS' to date, else None."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(s), fmt).date()
        except Exception:
            pass
    return None

def human_range(start_s, end_s):
    """
    Return a compact, human-friendly label for a date range.
      - Same month & year:  Nov 01–07, 2025
      - Same year, diff months: Oct 31 – Nov 06, 2025
      - Diff years: Dec 31, 2025 – Jan 06, 2026
    """
    sd = _parse_any_date(start_s)
    ed = _parse_any_date(end_s)
    if not sd or not ed:
        return f"{start_s} – {end_s}"

    if sd == ed:
        return sd.strftime("%b %d, %Y")

    if sd.year == ed.year:
        if sd.month == ed.month:
            # Nov 01–07, 2025
            return f"{sd.strftime('%b %d')}–{ed.strftime('%d, %Y')}"
        else:
            # Oct 31 – Nov 06, 2025
            return f"{sd.strftime('%b %d')} – {ed.strftime('%b %d, %Y')}"
    else:
        # Dec 31, 2025 – Jan 06, 2026
        return f"{sd.strftime('%b %d, %Y')} – {ed.strftime('%b %d, %Y')}"

def _librarian_kpi_table(acct, styles, date_range_label):
    bio = acct.get("bio", {}) or {}
    perf = acct.get("performance", {}) or {}
    status = (bio.get("status") or "—").upper()
    created_when = bio.get("created_on")  
    # 🔥 NEW GUARD: skip KPI if created after report end date
    created_date = None
    if created_when and created_when not in ("—", ""):
        try:
            created_date = datetime.strptime(str(created_when), "%Y-%m-%d").date()
        except Exception:
            created_date = None

    end_d = datetime.today().date()
    if "meta" in acct and "end_date" in acct["meta"]:
        try:
            end_d = datetime.fromisoformat(acct["meta"]["end_date"]).date()
        except Exception:
            pass

    if created_date and created_date > end_d:
        return Table([["Evaluation Criteria", "Metrics"], ["—", "Account not created in this period."]]), \
               "Account not created in this period."

    # --- Existing logic unchanged below ---
    age_days = bio.get("days_old")  # always pull raw days
    uploads_in_range = perf.get("uploads_in_window", 0)

    # Build KPI table
    
    if age_days in (None, "—"):
        age_display = "—"
    else:
        if status == "NEW":
            age_display = f"Created {age_days} day(s) ago"
        elif status == "ACTIVE":
            age_display = f"Active for {age_days} day(s)"
        else:
            age_display = f"{age_days} day(s)"

    rows = [
        ["Evaluation Criteria", "Metrics"],
        ["Account Status", status],
        ["Date Created", _format_date_words(created_when)],
        ["Account Age", age_display],
        ["Books/Thesis Upload", str(uploads_in_range)],
    ]
    tbl = Table(rows, colWidths=[1.5*inch, 1.7*inch])
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.6, MAROON),
        ('BOX', (0,0), (-1,-1), 0.9, MAROON),
        ('BACKGROUND', (0,0), (-1,0), MAROON),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 10),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROSE]),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 10),
    ]))

    # --- Remark Logic ---
    range_label = (date_range_label or "the selected range").lower()
    if "week" in range_label:
        threshold = 3
        scope_text = f"this {date_range_label}"
    elif "month" in range_label:
        threshold = 7
        scope_text = f"this {date_range_label}"
    elif "year" in range_label:
        threshold = 20
        scope_text = f"this {date_range_label}"
    elif "all time" in range_label:
        threshold = 50
        scope_text = "for the whole period of using the system"
    else:
        threshold = 5  # fallback if unknown range
        scope_text = f"during {date_range_label}"

    if status == "NEW":
        if age_days not in (None, "—") and int(age_days) >= 5 and uploads_in_range == 0:
            remark = (
                f"This account was created {age_days} day(s) ago, but has <b>not been accessed.</b> "
                f"Consider reaching out to check if the user is having trouble logging in or "
                f"needs guidance on how to start using the system."
            )
        else:
            remark = (
                f"<b>New account</b>: Created {age_days} day(s) ago. "
                f"Monitoring is recommended to ensure the user begins participating."
            )
    elif status == "DEACTIVATED":
        remark = (
            f"<b>Deactivated account</b>: This account is no longer active in the system. "
        )
    
    elif uploads_in_range < threshold:
        remark = f"<b>Low activity</b>: {uploads_in_range} upload(s) {scope_text}. " \
                f"Consider reaching out to understand challenges and offer support."
    elif uploads_in_range == threshold:
        remark = f"<b>Activity level</b>: {uploads_in_range} upload(s) {scope_text}. " \
                f"Performance is on track. Continue maintaining consistent contributions."
    else:
        remark = f"<b>High activity</b>: {uploads_in_range} upload(s) {scope_text}. " \
                f"Excellent performance—commendable contribution."



    return tbl, remark


def _admin_kpi_table(acct, styles, context):
    bio = acct.get("bio", {}) or {}
    perf = acct.get("performance", {}) or {}

    status = (bio.get("status") or "—").upper()

    # Use created_when from UserAccounts (stored in bio as created_on or days_old)
    created_when = bio.get("created_on")
    age_days = bio.get("days_old")  # always pull raw days


    # New logic for Account Age display
    if age_days in (None, "—"):
        age_display = "—"
    else:
        if status == "NEW":
            age_display = f"Created {age_days} day(s) ago"
        elif status == "ACTIVE":
            age_display = f"Active for {age_days} day(s)"
        elif status == "DEACTIVATED":
            age_display = "(Inactive)"   
        else:
            age_display = f"{age_days} day(s)"



    # ✅ Use consistent key from payload
    created_count = perf.get("created_in_window", 0)

    rows = [
        ["Evaluation Criteria", "Metrics"],
        ["Account Status", status],
        ["Date Created", _format_date_words(created_when)],
        ["Account Age", age_display],  # 🟢 updated line
        ["Accounts Created", str(created_count)],
    ]

    tbl = Table(rows, colWidths=[1.5*inch, 1.7*inch])
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.6, MAROON),
        ('BOX', (0,0), (-1,-1), 0.9, MAROON),
        ('BACKGROUND', (0,0), (-1,0), MAROON),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 10),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROSE]),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 10),
    ]))

    # Build summary remark listing surnames of accounts created by this admin
    range_label = context.get("meta", {}).get("range_label", "the selected range")
    if range_label.lower() == "all time":
        scope_text = "for the whole period of using the system"
    else:
        scope_text = f"during {range_label}"

    created_accounts = perf.get("created_accounts_list", [])

    # New logic for NEW admin accounts
    if status == "NEW":
        if age_days not in (None, "—") and int(age_days) >= 5 and created_count == 0:
            remark = (
                f"This administrator account was created {age_days} day(s) ago, but has <b>not been accessed.</b> "
                f"Consider reaching out to check if the user is having trouble logging in or "
                f"needs guidance on how to use the system."
            )
        else:
            remark = (
                f"<b>New administrator</b>: Created {age_days} day(s) ago. "
                f"Monitoring is recommended to ensure the admin begins participating."
            )
            
    elif status == "DEACTIVATED":
        remark = (
            f"<b>Deactivated account</b>: This account is no longer active in the system. "
        )

    # Existing admins
    elif created_count > 0 and created_accounts:
        remark = "This administrator created the following accounts " + scope_text + ": " + ", ".join(created_accounts)
    else:
        remark = f"No accounts were created by this administrator {scope_text}."


    return tbl, remark
    
def _department_kpi_table(acct, styles, context):
    """KPI table and remarks for Department role — same logic as Librarian but with department-specific remarks."""
    bio = acct.get("bio", {}) or {}
    perf = acct.get("performance", {}) or {}

    status = (bio.get("status") or "—").upper()
    created_when = bio.get("created_on")
    age_days = bio.get("days_old")  # same as librarian logic
    uploads_in_range = perf.get("uploads_in_window", 0)

    # Account age display (copied from librarian logic)
    if age_days in (None, "—"):
        age_display = "—"
    else:
        if status == "NEW":
            age_display = f"Created {age_days} day(s) ago"
        elif status == "ACTIVE":
            age_display = f"Active for {age_days} day(s)"
        else:
            age_display = f"{age_days} day(s)"

    # --- KPI Table ---
    rows = [
        ["Evaluation Criteria", "Metrics"],
        ["Account Status", status],
        ["Date Created", _format_date_words(created_when)],
        ["Account Age", age_display],
        ["Books/Thesis Upload", str(uploads_in_range)],
    ]

    tbl = Table(rows, colWidths=[1.5*inch, 1.7*inch])
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.6, MAROON),
        ('BOX', (0,0), (-1,-1), 0.9, MAROON),
        ('BACKGROUND', (0,0), (-1,0), MAROON),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 10),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROSE]),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 10),
    ]))

    # --- Remark logic (same thresholds as librarian) ---
    range_label = (context.get("meta", {}) or {}).get("range_label", "the selected range").lower()
    if "week" in range_label:
        threshold = 3
        scope_text = f"this {context.get('meta', {}).get('range_label')}"
    elif "month" in range_label:
        threshold = 7
        scope_text = f"this {context.get('meta', {}).get('range_label')}"
    elif "year" in range_label:
        threshold = 20
        scope_text = f"this {context.get('meta', {}).get('range_label')}"
    elif "all time" in range_label:
        threshold = 50
        scope_text = "for the whole period of using the system"
    else:
        threshold = 5
        scope_text = f"during {context.get('meta', {}).get('range_label')}"

    # --- Department-specific remarks (paraphrased for non-library departments) ---
    if status == "NEW":
        if age_days not in (None, "—") and int(age_days) >= 5 and uploads_in_range == 0:
            remark = (
                f"This department account was created {age_days} day(s) ago, but has <b>not uploaded any materials yet.</b> "
                f"Departments with their own collections are encouraged to start scanning and uploading resources "
                f"to keep their mini-library updated."
            )
        else:
            remark = (
                f"<b>New department account</b>: Created {age_days} day(s) ago. "
                f"Monitor its initial use to ensure staff begin uploading or updating their departmental materials."
            )

    elif status == "DEACTIVATED":
        remark = (
            f"<b>Deactivated account</b>: This department is currently inactive in the system. "
            f"Reactivation may be considered if this department account plans to continue maintaining digital collections."
        )

    elif uploads_in_range < threshold:
        remark = (
            f"<b>Low activity</b>: Only {uploads_in_range} upload(s) {scope_text}. "
            f"Encourage this department account to digitize and upload more materials from their mini-library "
            f"to increase visibility and access."
        )

    elif uploads_in_range == threshold:
        remark = (
            f"<b>Steady activity</b>: {uploads_in_range} upload(s) {scope_text}. "
            f"This department account is maintaining an acceptable level of contribution to the Liraya System."
        )

    else:
        remark = (
            f"<b>High activity</b>: {uploads_in_range} upload(s) {scope_text}. "
            f"This department account demonstrates steady engagement in managing and sharing academic materials."
        )

    return tbl, remark



def _account_card_block(acct, styles, context):
    """Account card with role-specific KPI (Admin vs Librarian) using old side-by-side layout."""
    bio = acct["bio"]

    # Profile picture
    pp_url = bio.get("profile_picture_url")
    left = _fetch_image_from_url(pp_url, width=1.0*inch, height=1.0*inch)

    header = Table([[left, _info_rows(bio)]], colWidths=[1.2*inch, 4.0*inch])
    header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))

    personal_tbl = _personal_info_table(bio, styles)

    # Role-based KPI
    role = (bio.get("role") or "").upper()
    if role == "LIBRARIAN":
        kpi_tbl, remark_text = _librarian_kpi_table(acct, styles, context.get("meta", {}).get("range_label", ""))
    elif role == "ADMIN":
        kpi_tbl, remark_text = _admin_kpi_table(acct, styles, context)
    elif role == "DEPARTMENT":
        kpi_tbl, remark_text = _department_kpi_table(acct, styles, context)
    else:
        kpi_tbl, remark_text = Table([["No KPI defined", "—"]]), ""

    # Summary remark with KeepInFrame to prevent overflow
    summary_para = Paragraph(remark_text, styles["Cell"]) if remark_text else Spacer(1, 0)
    summary_box = KeepInFrame(
        maxWidth=2.10*inch,   # summary column width
        maxHeight=1.10*inch,  # prevent overlapping
        content=[summary_para],
        mode="shrink"         # shrink text if too long
    )

    # Layout side-by-side (like old version)
    KPI_W     = 3.20*inch   # KPI table width
    GUTTER_W  = 0.18*inch   # space between table and summary
    SUMMARY_W = 2.10*inch   # summary width

    bottom = Table(
        [[kpi_tbl, Spacer(1, 1), summary_box]],
        colWidths=[KPI_W, GUTTER_W, SUMMARY_W]
    )
    bottom.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),

        # Zero out default paddings
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 0),

        # KPI cell padding
        ('LEFTPADDING',  (0,0), (0,0), 6),
        ('RIGHTPADDING', (0,0), (0,0), 6),
        ('TOPPADDING',   (0,0), (0,0), 4),
        ('BOTTOMPADDING',(0,0), (0,0), 4),

        # Summary cell padding
        ('LEFTPADDING',  (2,0), (2,0), 8),
        ('RIGHTPADDING', (2,0), (2,0), 6),
        ('TOPPADDING',   (2,0), (2,0), 4),
        ('BOTTOMPADDING',(2,0), (2,0), 4),
    ]))

    card = [
        header,
        Spacer(1, 6),
        Paragraph("<b>Personal Information</b>", styles["SectionTitle"]),
        personal_tbl,
        Spacer(1, 40),
        bottom,
    ]
    outer = Table([[card]], colWidths=[6.7*inch])
    outer.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    return outer





def _pie_image(labels, sizes, title=None, width=3.1*inch):
    """
    Render a pie chart to an in-memory PNG and return it as a ReportLab Image.
    Uses conservative label/pct placement to reduce overlap.
    """
    # Normalize inputs
    labels = [str(l) for l in (labels or [])]
    sizes  = [int(s) for s in (sizes or [])]

    if not labels or not sizes or sum(sizes) == 0:
        # No data -> spacer so layout doesn't break
        return Spacer(1, width * 0.75)

    fig, ax = plt.subplots(figsize=(3.3, 3.3), dpi=120)
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        startangle=90,
        counterclock=False,
        autopct=lambda p: f"{p:.0f}%" if p >= 8 else "",  # only show % if >= 8% to reduce clutter
        pctdistance=0.72,                                  # move % closer to center
        labeldistance=1.12,                                # push labels outward
        wedgeprops=dict(linewidth=0.5, edgecolor="white")
    )
    # Small font to avoid collisions
    for t in texts + autotexts:
        t.set_fontsize(8)

    ax.axis('equal')  # keep it circular

    if title:
        ax.set_title(title, fontsize=10, pad=8)

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width, height=width)

def _deactivation_recommendations(context):
    """
    Two rules:
      1) ACTIVE but poor performance: no uploads/creates in the last 7+ days
      2) NEW for >= 7 days (no signs of activity)
    Yields rows: [name, status, created, reason]
    """
    recs = []
    
    # NEW: parse report end date from context
    end_d = datetime.today().date()
    if "meta" in context and "end_date" in context["meta"]:
        try:
            end_d = datetime.fromisoformat(context["meta"]["end_date"]).date()
        except Exception:
            pass
        
    for acct in context.get("accounts", []):
        bio  = acct.get("bio", {}) or {}
        perf = acct.get("performance", {}) or {}

        name    = bio.get("full_name") or bio.get("username") or "—"
        status  = (bio.get("status") or "").upper() or "—"
        created = bio.get("created_at") or bio.get("date_joined") or "—"
        role    = (bio.get("role") or "").upper()
        
        #  NEW GUARD: skip if account created after end_d
        created_date = None
        if created and created not in ("—", ""):
            try:
                created_date = datetime.strptime(str(created), "%Y-%m-%d").date()
            except Exception:
                try:
                    created_date = datetime.strptime(str(created), "%Y-%m-%dT%H:%M:%S").date()
                except Exception:
                    created_date = None

        if created_date and created_date > end_d:
            continue

        uploads_7d             = perf.get("uploads_7d")
        created_in_window      = perf.get("created_in_window")
        days_since_last_upload = perf.get("days_since_last_upload")

        # Fallback if not provided in performance data
        if days_since_last_upload is None and created_date is not None:
            days_since_last_upload = max((end_d - created_date).days, 1)
            
        days_in_status = (
            perf.get("days_in_status")
            or perf.get("days_since_created")
            or bio.get("days_since_created")
        )

        reason = None

        # Rule 1: Active accounts with low or no recent activity
        no_recent_activity = (
            (uploads_7d is not None and uploads_7d == 0)
            and (created_in_window is not None and created_in_window == 0)
        ) or (days_since_last_upload is not None and days_since_last_upload > 7)

        if status == "ACTIVE" and role in ("LIBRARIAN", "DEPARTMENT") and no_recent_activity:
            days_text = f"{days_since_last_upload} days"
            reason = f"Active but no uploads in the last {days_text}"

        # Rule 2: New accounts inactive for a while
        if reason is None and status == "NEW" and (days_in_status is not None and days_in_status >= 7):
            reason = f"Account registered {days_in_status} days ago with no initial login detected"


        if reason:
            recs.append([name, status, created, reason])

    return recs

def _reco_table(context, styles):
    """Maroon header, zebra rows, wrapped text."""
    rows = [["Name", "Status", "Created on", "Reason"]]
    data = _deactivation_recommendations(context)
    if data:
        for name, status, created, reason in data[:18]:
            rows.append([
                Paragraph(name, styles["Cell"]),
                Paragraph(status, styles["Cell"]),
                Paragraph(_format_date_words(created), styles["Cell"]),
                Paragraph(reason, styles["Cell"]),
            ])
    else:
        rows.append(["—", "—", "—", "No accounts meet the criteria."])

    # total width ≈ 6.7"
    tbl = Table(rows, colWidths=[2.3*inch, 1.0*inch, 1.4*inch, 2.0*inch])
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.8, MAROON),
        ('BOX',  (0,0), (-1,-1), 0.9, MAROON),

        ('BACKGROUND', (0,0), (-1,0), MAROON),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONT',       (0,0), (-1,0), 'Helvetica-Bold', 10),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),

        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROSE]),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 9),
        ('FONT', (0,1), (0,-1), 'Helvetica-Bold', 9),  # names bold

        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING',   (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]))
    return tbl

def _low_activity_librarians(context, styles):
    """
    Table of librarians with low activity. Total uses the same KPI metric
    'uploads_in_window'; thesis/books are just a breakdown.
    """
    range_label = (context.get("meta", {}) or {}).get("range_label", "the selected range").lower()

    if "week" in range_label:
        threshold = 3
    elif "month" in range_label:
        threshold = 7
    elif "year" in range_label:
        threshold = 20
    elif "all time" in range_label:
        threshold = 50
    else:
        threshold = 5

    rows = [["No.", "Name of Librarian", "Thesis Uploads", "Book Uploads", "Total Uploads"]]
    low_rows = []
    for acct in context.get("accounts", []):
        bio  = acct.get("bio", {}) or {}
        perf = acct.get("performance", {}) or {}
        if (bio.get("role") or "").upper() != "LIBRARIAN":
            continue

        total = int(perf.get("uploads_in_window", 0))
        if total >= threshold:
            continue

        name   = bio.get("full_name") or bio.get("username") or "—"
        thesis = int(perf.get("thesis_in_window", 0))
        books  = int(perf.get("books_in_window", 0))
        low_rows.append([name, thesis, books, total])

    if low_rows:
        for i, (name, thesis, books, total) in enumerate(low_rows, 1):
            rows.append([str(i), name, str(thesis), str(books), str(total)])
    else:
        rows.append(["—", "No librarians meet the low activity criteria.", "—", "—", "—"])

    tbl = Table(rows, colWidths=[0.6*inch, 2.6*inch, 1.2*inch, 1.2*inch, 1.1*inch])
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.8, MAROON),
        ('BOX', (0,0), (-1,-1), 0.9, MAROON),
        ('BACKGROUND', (0,0), (-1,0), MAROON),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONT',       (0,0), (-1,0), 'Helvetica-Bold', 9),
        ('ALIGN',      (0,0), (-1,0), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROSE]),
        ('FONT', (0,1), (-1,-1), 'Helvetica', 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING',   (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]))
    return tbl

def _admin_created_accounts_table(context, styles):
    """
    One table, two columns:
      - Name of Admin  (pink cells)
      - Accounts Created (full names, based on the selected range)
    Uses data already bundled into context["accounts"] by generate_pdf().
    """
    rows = [["Name of Admin", "Accounts Created (Full Names)"]]
    admins_found = False

    for acct in context.get("accounts", []):
        bio  = acct.get("bio", {}) or {}
        perf = acct.get("performance", {}) or {}
        role = (bio.get("role") or "").upper()

        if role != "ADMIN":
            continue

        created_count = int(perf.get("created_in_window", 0) or 0)
        names = perf.get("created_accounts_fullnames") or []

        # Skip admins with nothing created in-range to keep table compact
        if created_count <= 0 and not names:
            continue

        admins_found = True
        admin_name = bio.get("full_name") or bio.get("username") or "—"

        # Numbered list: "1. Name", "2. Name", ... (line breaks for wrapping)
        names_html = "—" if not names else "<br/>".join(
            f"{i}. {n}" for i, n in enumerate(names, 1)
        )

        rows.append([
            Paragraph(admin_name, styles["Cell"]),
            Paragraph(names_html, styles["Cell"]),
        ])

    if not admins_found:
        rows.append([
            Paragraph("—", styles["Cell"]),
            Paragraph("No accounts were created in this period.", styles["Cell"]),
        ])

    # total width ≈ 6.7"
    tbl = Table(rows, colWidths=[2.4*inch, 4.3*inch])
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.8, MAROON),
        ('BOX',  (0,0), (-1,-1), 0.9, MAROON),

        # Header
        ('BACKGROUND', (0,0), (-1,0), MAROON),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONT',       (0,0), (-1,0), 'Helvetica-Bold', 10),
        ('ALIGN',      (0,0), (-1,0), 'CENTER'),

        # Pink admin column (body only)
        ('BACKGROUND', (0,1), (0,-1), ROSE),
        ('TEXTCOLOR',  (0,1), (0,-1), colors.black),
        ('FONT',       (0,1), (0,-1), 'Helvetica-Bold', 9),

        # Body font for right column
        ('FONT',       (1,1), (1,-1), 'Helvetica', 9),

        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING',   (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]))
    return tbl

CONTENT_WIDTH = 6.7*inch  # keep this consistent

def _section_title(text, styles, left_pad=6, right_pad=6):
    """Title aligned with the content tables (uses same padding)."""
    t = Table([[Paragraph(text, styles["SectionTitle"])]],
              colWidths=[CONTENT_WIDTH])
    t.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0), (-1,-1), left_pad),
        ('RIGHTPADDING', (0,0), (-1,-1), right_pad),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 0),
    ]))
    return t

def _section_text(html, styles, left_pad=6, right_pad=6):
    """Body text directly under a section title, aligned the same."""
    t = Table([[Paragraph(html, styles["SmallBlack"])]],
              colWidths=[CONTENT_WIDTH])
    t.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0), (-1,-1), left_pad),
        ('RIGHTPADDING', (0,0), (-1,-1), right_pad),
        ('TOPPADDING',   (0,0), (-1,-1), 2),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
    ]))
    return t

CONTENT_WIDTH = 6.7*inch  # keep consistent with your layout

def _section_title_center(text, styles):
    t = Table([[Paragraph(text, styles["SectionTitleCenter"])]],
              colWidths=[CONTENT_WIDTH])
    t.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
    ]))
    return t



def generate_account_information(output_stream, context):
    header_height = get_header_height()
    footer_height = get_footer_height()

    doc = SimpleDocTemplate(
        output_stream,
        pagesize=letter,
        topMargin=header_height,
        bottomMargin=footer_height
    )

    styles = _style_sheet()
    flow = []

    # Centered banner + range/generated-by table
    flow.extend(_center_banner(context.get("meta", {}), styles))

    # Individual cards (one per page)
    mode = context.get("meta", {}).get("mode", "")

    if mode == "with_biodata":
        first = True
        for acct in context.get("accounts", []):
            if not first:
                flow.append(PageBreak())
            first = False
            flow.append(_account_card_block(acct, styles, context))
        flow.append(PageBreak())  # only for full biodata runs
    elif mode == "summary_only":
        flow.append(Spacer(1, 10))  # small gap, no page break
    

    # ---- Overall Summary ----
    flow.append(_section_title("Overall Summary", styles))
    flow.append(Spacer(1, 6))
    
    totals  = (context.get("summary") or {}).get("totals") or {}
    roles   = totals.get("roles", {}) or {}
    status  = totals.get("status", {}) or {}

    # Format range for human-readable titles
    meta = (context.get("meta") or {})
    start_s   = meta.get("start_date")
    end_s     = meta.get("end_date")
    raw_label = (meta.get("range_label") or "").strip()

    rl_lower = raw_label.lower()

    if rl_lower == "all time":
        scope_text = "overall"
    else:
        # 1) Try to honor the label first (month/year/etc.)
        parsed_ok = False
        for fmt in ("%b %Y", "%B %Y"):  # e.g., "Sep 2025" or "September 2025"
            try:
                dt = datetime.strptime(raw_label, fmt)
                scope_text = "during " + dt.strftime("%B %Y")
                parsed_ok = True
                break
            except Exception:
                pass
        if not parsed_ok:
            try:
                dt = datetime.strptime(raw_label, "%Y")  # e.g., "2025"
                scope_text = "during " + dt.strftime("%Y")
                parsed_ok = True
            except Exception:
                pass

        # 2) If label didn't parse, fall back to actual dates if present
        if not parsed_ok and start_s and end_s:
            scope_text = "during " + human_range(start_s, end_s)
        # 3) Last resort: just echo the label
        if not parsed_ok and not (start_s and end_s):
            scope_text = "during " + (raw_label or "the selected range")

    data = [
        ["Category", "Count"],
        ["Total Accounts", str(totals.get("accounts", 0))],
        ["Admin Account(s)",         str(roles.get("ADMIN", 0))],
        ["Librarian Account(s)",     str(roles.get("LIBRARIAN", 0))],
        ["Department Account(s)",    str(roles.get("DEPARTMENT", 0))],
        ["NEW",           str(status.get("NEW", 0))],
        ["ACTIVE",        str(status.get("ACTIVE", 0))],
        ["DEACTIVATED",   str(status.get("DEACTIVATED", 0))],
        [f"Accounts created {scope_text}", str(totals.get("accounts_created_in_window", 0))],
        [f"Uploads {scope_text}",          str(totals.get("uploads_in_window", 0))],
        [f"Active uploaders {scope_text}", str(totals.get("active_uploaders_in_window", 0))],
    ]
    tbl = Table(data, colWidths=[3.4*inch, 3.2*inch])
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.8, MAROON),
        ('BOX',  (0,0), (-1,-1), 0.9, MAROON),

        ('BACKGROUND', (0,0), (-1,0), MAROON),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONT',       (0,0), (-1,0), 'Helvetica-Bold', 10),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),   


        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROSE]),
        ('TEXTCOLOR',      (0,1), (-1,-1), colors.black),
        ('FONT', (0,1), (0,-1), 'Helvetica-Bold', 10),

        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING',   (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),

        ('ALIGN', (1,1), (1,-1), 'CENTER'),
    ]))
    flow.append(tbl)
    flow.append(Spacer(1, 4))


    # Pie charts (two side-by-side)
    role_labels   = list(roles.keys());   role_sizes   = [roles[k] for k in role_labels]
    status_labels = list(status.keys());  status_sizes = [status[k] for k in status_labels]
    img_roles  = _pie_image(role_labels, role_sizes, title="Roles")
    img_status = _pie_image(status_labels, status_sizes, title="Account Status")
    charts_tbl = Table([[img_roles, img_status]], colWidths=[3.35*inch, 3.35*inch])
    charts_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    flow.append(charts_tbl)
    # --- Dynamic Pie Chart Summary ---
    role_admin     = roles.get("ADMIN", 0)
    role_librarian = roles.get("LIBRARIAN", 0)
    role_department = roles.get("DEPARTMENT", 0)
    status_new     = status.get("NEW", 0)
    status_active  = status.get("ACTIVE", 0)
    status_deact   = status.get("DEACTIVATED", 0)

    remarks = []

    # --- Paragraph 1: Librarian, Admin, and Department Summary ---
    if role_librarian <= 5 or role_admin <= 3:
        parts = []
        if role_librarian <= 5:
            parts.append(f"<b>{role_librarian}</b> librarian(s)")
        if role_admin <= 3:
            parts.append(f"<b>{role_admin}</b> administrator(s)")
        staff_text = " and ".join(parts)
        para1 = (
            f"The report shows that there are only {staff_text}. Having too few staff may "
            f"affect how well the system is monitored, supported, and managed. "
            f"Adding more staff accounts is recommended to improve system efficiency."
        )
    else:
        para1 = (
            f"The report shows that staffing levels are stable, with "
            f"<b>{role_librarian}</b> librarian(s) and <b>{role_admin}</b> administrator(s). "
            f"This indicates that the system is properly supported and managed."
        )

    # --- Department Logic (Integrated in same paragraph) ---
    dept_uploads = sum(
        acct.get("performance", {}).get("uploads_in_window", 0)
        for acct in context.get("accounts", [])
        if (acct.get("bio", {}).get("role") or "").upper() == "DEPARTMENT"
    )

    range_label = (context.get("meta", {}) or {}).get("range_label", "").lower()
    if "week" in range_label:
        threshold = 3
        scope_text = f"this {context.get('meta', {}).get('range_label')}"
    elif "month" in range_label:
        threshold = 7
        scope_text = f"this {context.get('meta', {}).get('range_label')}"
    elif "year" in range_label:
        threshold = 20
        scope_text = f"this {context.get('meta', {}).get('range_label')}"
    elif "all time" in range_label:
        threshold = 50
        scope_text = "for the whole period of using the system"
    else:
        threshold = 5
        scope_text = f"during {context.get('meta', {}).get('range_label')}"

    # Now generate Department summary text (same structure as Librarian KPI)
    if role_department > 0:
        if dept_uploads == 0:
            dept_text = (
                f" Meanwhile, there are <b>{role_department}</b> department account(s), "
                f"but none have uploaded materials yet. Encouraging each department to begin "
                f"uploading thesis or academic books will help expand the digital collection "
                f"that students can search and borrow."
            )
        elif dept_uploads < threshold:
            dept_text = (
                f" Additionally, there are <b>{role_department}</b> department account(s) "
                f"with a total of <b>{dept_uploads}</b> upload(s) {scope_text}. "
                f"This indicates low participation; department accounts are encouraged to upload more "
                f"academic materials to enhance access for student researchers."
            )
        elif dept_uploads == threshold:
            dept_text = (
                f" Moreover, there are <b>{role_department}</b> department account(s) contributing "
                f"<b>{dept_uploads}</b> upload(s) {scope_text}. "
                f"This reflects consistent departmental engagement in maintaining mini-libraries "
                f"and supporting academic access."
            )
        else:
            dept_text = (
                f" Furthermore, <b>{role_department}</b> department account(s) have collectively "
                f"uploaded <b>{dept_uploads}</b> materials {scope_text}. "
                f"This shows active participation in preserving and sharing theses or academic books "
                f"that students can search and borrow."
            )
    else:
        dept_text = (
            " Currently, no department accounts are registered in the system. "
            "Departments are encouraged to create accounts and upload theses or academic books "
            "to expand the searchable and borrowable collection available to students."
        )

    # Combine both sections into a unified summary paragraph
    remarks.append(para1 + dept_text)

    # --- Paragraph 2: Account Activity Summary (existing logic) ---
    total_inactive_like = status_new + status_deact
    total_new_and_active = status_new + status_active

    if total_new_and_active == 0:
        remarks.append(
            "It is also concerning that there are no ACTIVE or NEW accounts in the system. "
            "This indicates that no accounts have been created or are currently active."
        )
    elif total_inactive_like > status_active:
        remarks.append(
            f"Additionally, it is concerning that NEW (<b>{status_new}</b>) and DEACTIVATED (<b>{status_deact}</b>) "
            f"accounts together total <b>{total_inactive_like}</b>, which exceeds the number of ACTIVE "
            f"accounts (<b>{status_active}</b>). This may suggest declining engagement or instability "
            f"in account usage."
        )
    else:
        remarks.append(
            f"The report also shows a positive trend: ACTIVE accounts (<b>{status_active}</b>) are greater "
            f"than the combined NEW (<b>{status_new}</b>) and DEACTIVATED (<b>{status_deact}</b>) "
            f"accounts (<b>{total_inactive_like}</b>). This indicates healthy system participation and "
            f"strong user engagement."
        )

    # Final summary paragraph
    summary_text = " ".join(remarks)
    flow.append(Paragraph(summary_text, styles["SmallBlack"]))


    # space before recommendations section
    mode = context.get("meta", {}).get("mode", "")
    if mode == "with_biodata":
        flow.append(PageBreak())
    else:
        flow.append(Spacer(1, 16))  # small space before next section

    # Recommendations (BELOW the pies)
    flow.append(_section_title_center("Accounts Recommended for Deactivation", styles))
    flow.append(_reco_table(context, styles))
    flow.append(Paragraph(
        "Criteria: (1) Active but no uploads in the last 7+ days; "
        "(2) Account registered ≥7 days ago but user never logged in.",
        styles["SmallGray"]
    ))  # <-- closed properly
    
    # ---- Low Activity Librarians ----
    flow.append(Spacer(1, 14))
    flow.append(_section_title_center("List of Librarians with Low Activity Remarks", styles))
    flow.append(_low_activity_librarians(context, styles))
    
    # Add a gentle, formal remark below the table
    flow.append(Paragraph(
        "Note: The listed librarians have shown lower activity. "
        "It is recommended to engage with them to better understand possible challenges and "
        "extend guidance or support that may encourage more active participation.",
        styles["SmallGray"]
    ))
    
        # ---- Admins and the accounts they created (within range) ----
    flow.append(Spacer(1, 14))
    flow.append(_section_title_center("Accounts Created by Admins", styles))
    flow.append(_admin_created_accounts_table(context, styles))
    
    # Add a gentle, formal remark below the table
    flow.append(Paragraph(
        "Note: This does not represent the complete list of administrators. "
        "The data shown only includes administrators who have created an account "
        "within the system.",
        styles["SmallGray"]
    ))


    # Build
    doc.build(flow, onFirstPage=create_header_and_footer, onLaterPages=create_header_and_footer)

# - - - - - - - -  - - - Keyword Report - - - - - - -- - - - - - - - - - - - - - - - - - - - #

def _generate_bar_image(labels, counts, ylabel='Searches'):
    path = os.path.join(tempfile.gettempdir(), f"bar_{uuid4().hex}.png")
    plt.figure(figsize=(6, 4))
    plt.bar(range(len(labels)), counts)
    rotation = 45 if len(labels) > 8 else 0
    plt.xticks(range(len(labels)), labels, rotation=rotation)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    return path

# --- Self-contained helpers (used by this report only) ---

def _has_results_like_html(log):
    """
    Mirror the HTML/Jinja truthiness used in the template:
      {% if log.books %} -> truthy means HAS results
    So 'no results' == not log.books (falsy).
    """
    val = getattr(log, "books", None)

    # Falsy -> no results
    if val is None:
        return False

    # Lists / tuples
    if isinstance(val, (list, tuple)):
        return len(val) > 0

    # Numeric
    if isinstance(val, (int, float)):
        try:
            return int(val) > 0
        except Exception:
            return False

    # Strings
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return False  # empty string is falsy -> no results
        # If it's a JSON list string, use its length
        if s.startswith('[') and s.endswith(']'):
            import json
            try:
                arr = json.loads(s)
                return isinstance(arr, list) and len(arr) > 0
            except Exception:
                # Invalid JSON string: HTML would still treat non-empty string as truthy -> has results
                return True
        # Any other non-empty string is truthy in the template -> has results
        return True

    # Anything else: try len(), fallback to bool
    try:
        return len(val) > 0
    except Exception:
        return bool(val)


def _title_case_name(name: str) -> str:
    if not name:
        return "—"
    return " ".join(str(name).strip().split()).title()

def _fmt_dt_local(dt):
    # tolerates None
    from django.utils import timezone
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M") if dt else "—"

def _parse_first_last(search_times_str):
    """
    search_times lines like:
      2025-10-24 13:04:12.123456
      2025-10-24 15:42:09
    Returns (first_str, last_str) in "%Y-%m-%d %H:%M" (localized).
    """
    if not search_times_str:
        return None, None
    parts = [p.strip() for p in str(search_times_str).splitlines() if p.strip()]
    if not parts:
        return None, None

    from django.utils import timezone
    from datetime import datetime
    def _to_dt(s):
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(s, fmt)
                return timezone.make_aware(dt)
            except Exception:
                pass
        return None

    dts = [dt for dt in (_to_dt(p) for p in parts) if dt]
    if not dts:
        return None, None

    first = min(dts)
    last  = max(dts)
    return _fmt_dt_local(first), _fmt_dt_local(last)

def _normalize_book_count(log):
    """
    STRICT: return >0 only when we have unambiguous evidence of results.
    Anything ambiguous (including non-JSON strings) counts as 0.
    """
    # 1) Preferred numeric field (rename if your model uses a different one)
    if hasattr(log, "total_book_results"):
        try:
            n = int(getattr(log, "total_book_results") or 0)
            return max(0, n)
        except Exception:
            return 0

    # 2) Generic 'books' attribute (list/tuple/int/float/JSON-string)
    val = getattr(log, "books", None)
    if val is None:
        return 0

    # list / tuple
    if isinstance(val, (list, tuple)):
        try:
            return max(0, int(len(val)))
        except Exception:
            return 0

    # numeric
    if isinstance(val, (int, float)):
        try:
            return max(0, int(val))
        except Exception:
            return 0

    # JSON-encoded list string -> count its length
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return 0
        if s.startswith('[') and s.endswith(']'):
            import json
            try:
                arr = json.loads(s)
                return max(0, int(len(arr))) if isinstance(arr, list) else 0
            except Exception:
                return 0
        # IMPORTANT: non-JSON strings are AMBIGUOUS -> treat as 0
        return 0

    # Fallback: try len(); if it fails, treat as 0
    try:
        return max(0, int(len(val)))
    except Exception:
        return 0

def generate_keyword_search_history(output_pdf_buffer, context=None, user_info=None):
    """
    Page 1:
      - Smaller title
      - Header table (Generated by, Role, Date, Time)
      - FIGURE 1: TOTAL AMOUNT OF KEYWORDS SEARCHED (bar chart + description)

    Page 2:
      - FIGURE 2: TOTAL AMOUNT OF NEW KEYWORDS (bar chart + description)
        * Uses created_at as the basis for "new" keywords per bucket.
        * Totals count the number of NEW keywords (not total searches).

    Page 3:
      - TABLE: Keywords With No Book Results (aligned to selected time filter)
        * Computes "Book Results Count" the same way the user_search page derives the
          result total (mirrors fuzzy matching across title/author/primary_keyword),
          and only lists keywords with zero book results.
        * Sorted alphabetically by keyword (case-insensitive), empty strings last.
    """
    from django.utils import timezone
    from django.db.models import Q
    from datetime import timedelta
    import unicodedata
    import difflib as _difflib

    context = context or {}
    meta   = context.get("meta", {})
    stats  = context.get("stats", {})
    chart  = context.get("chart", {})
    # second figure (new keywords)
    stats2 = context.get("stats_new", {}) or stats
    chart2 = context.get("chart_new", {}) or chart

    # ======================
    # ===== Page 1/2 =======
    # ======================

    title_text = meta.get("title", "Keyword Search History Report")

    # ---- Page format ----
    header_height = get_header_height()
    footer_height = get_footer_height()
    doc = SimpleDocTemplate(output_pdf_buffer, pagesize=letter, title=title_text)
    doc.topMargin = header_height
    doc.bottomMargin = footer_height

    # ---- Styles ----
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']; style_normal.fontSize = 10

    # Smaller title
    title_header_style = ParagraphStyle(
        name='TitleHeaderStyle',
        fontName='Helvetica-Bold',
        fontSize=24,
        alignment=1,
        spaceAfter=16
    )
    title_topic_style = ParagraphStyle(
        name='TitleTopicStyle',
        fontName='Helvetica-Bold',
        fontSize=15,
        alignment=0,
        spaceAfter=10
    )
    content_style = styles['Normal']; content_style.fontSize = 10; content_style.leading = 12
    bold_label    = ParagraphStyle(name='BoldLabel',  parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10)
    table_text    = ParagraphStyle(name='TableText',  parent=styles['Normal'], fontName='Helvetica',      fontSize=10)

    flowables = []

    # ===== Page 1 =====
    flowables.append(Paragraph(title_text, title_header_style))
    flowables.append(Spacer(1, 12))

    generated_by_raw = (user_info or {}).get('full_name') or meta.get('generated_by', '—')
    generated_by   = _title_case_name(generated_by_raw)
    role           = (user_info or {}).get('role')           or meta.get('generated_by_role', '—')
    date_generated = (user_info or {}).get('date_generated') or '—'
    time_generated = (user_info or {}).get('time_generated') or meta.get('generated_at', '—')

    header_rows = [
        [Paragraph("<b>Generated by:</b>", bold_label), Paragraph(generated_by, table_text)],
        [Paragraph("<b>Role:</b>",          bold_label), Paragraph(role,         table_text)],
        [Paragraph("<b>Date Generated:</b>",bold_label), Paragraph(date_generated, table_text)],
        [Paragraph("<b>Time Generated:</b>",bold_label), Paragraph(time_generated, table_text)],
    ]
    header_table = Table(header_rows, colWidths=[2*inch, 4.5*inch], splitByRow=True)
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8d8c4')),
        ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
        ('TEXTCOLOR',  (0, 0), (-1, -1), colors.black),
        ('FONTNAME',   (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ('GRID',       (0, 0), (-1, -1), 1, colors.white),
    ]))
    flowables.append(header_table)
    flowables.append(Spacer(1, 10))

    # Figure 1
    flowables.append(Paragraph("FIGURE 1: TOTAL AMOUNT OF KEYWORDS SEARCHED", title_topic_style))
    flowables.append(Spacer(1, 5))

    labels = chart.get('labels') or ['All Time']
    counts = chart.get('counts') or [stats.get('total_searches', 0)]
    if len(counts) != len(labels):
        if len(counts) < len(labels):
            counts = list(counts) + [0] * (len(labels) - len(counts))
        else:
            counts = counts[:len(labels)]

    img_path1 = _generate_bar_image(labels, counts, ylabel='Searches')
    if img_path1 and os.path.exists(img_path1):
        flowables.append(Image(img_path1, width=6*inch, height=4*inch))
        flowables.append(Spacer(1, 10))

    total = int(stats.get("total_searches") or 0)
    start_date = stats.get("start_date", "—")
    end_date   = stats.get("end_date", "—")
    days       = int(stats.get("days") or 1)
    avg        = stats.get("average_per_day", 0)

    if total == 0:
        desc1 = (
            "Figure 1 bar graph represents the total keyword searches. "
            f"The data shown covers the period from {start_date} to {end_date}. "
            "No keywords were searched during this period yet."
        )
    else:
        desc1 = (
            "Figure 1 bar graph represents the total keyword searches. "
            f"The data shown covers the period from {start_date} to {end_date}, "
            f"with a total of {total} searches during this period. "
            "The bar indicates the overall accumulated searches from the earliest log to the most recent log. "
            f"The average searches per day during this period is {avg}. "
            f"This is calculated by dividing the total searches ({total}) by the number of days in the period ({days}), "
            f"resulting in {avg}. "
            "This shows that, on average, the system recorded that many keyword searches per day throughout the period."
        )
    flowables.append(Paragraph(desc1, content_style))

    # ===== Page 2 =====
    flowables.append(PageBreak())
    flowables.append(Paragraph("FIGURE 2: TOTAL AMOUNT OF NEW KEYWORDS", title_topic_style))
    flowables.append(Spacer(1, 5))

    labels2 = chart2.get('labels') or labels
    counts2 = chart2.get('counts')
    if not counts2:
        counts2 = [0] * len(labels2)
    elif len(counts2) != len(labels2):
        if len(counts2) < len(labels2):
            counts2 = list(counts2) + [0] * (len(labels2) - len(counts2))
        else:
            counts2 = counts2[:len(labels2)]

    img_path2 = _generate_bar_image(labels2, counts2, ylabel='New Keywords')
    if img_path2 and os.path.exists(img_path2):
        flowables.append(Image(img_path2, width=6*inch, height=4*inch))
        flowables.append(Spacer(1, 10))

    total2 = int(stats2.get("total_new_keywords") or sum(counts2))
    start_date2 = stats2.get("start_date", start_date)
    end_date2   = stats2.get("end_date", end_date)
    days2       = int(stats2.get("days") or days)
    avg2        = stats2.get("average_new_per_day", round(total2 / max(1, days2), 2))

    if total2 == 0:
        desc2 = (
            "Figure 2 bar graph represents the total number of new keywords. "
            f"The data shown covers the period from {start_date2} to {end_date2}. "
            "No new keywords were added during this period yet."
        )
    else:
        desc2 = (
            "Figure 2 bar graph represents the total number of new keywords. "
            f"The data shown covers the period from {start_date2} to {end_date2}, "
            f"with a total of {total2} new keywords during this period. "
            "Each bar indicates how many unique keywords were newly created within each time bucket. "
            f"The average new keywords per day during this period is {avg2}. "
            f"This is calculated by dividing the total new keywords ({total2}) by the number of days in the period ({days2}), "
            f"resulting in {avg2}. "
            "This shows that, on average, the system recorded that many newly created keywords per day throughout the period."
        )
    flowables.append(Paragraph(desc2, content_style))

    # ======================
    # ===== Page 3 =========
    # ======================
    flowables.append(PageBreak())
    flowables.append(Paragraph("FIGURE 3: KEYWORDS WITH NO BOOK RESULTS", title_topic_style))
    flowables.append(Spacer(1, 5))

    # ---------- Page 3: compute true "Book Results Count" ----------
    try:
        # Normalize/accept labels coming from UI
        tf_raw = (meta.get("range_label") or "all").strip()
        tf_key = tf_raw.lower().replace(' ', '').replace('_', '').replace('-', '')
        tf = (
            'last24hours' if tf_key in ('last24hours', 'last24h', '24h') else
            'last7days'   if tf_key in ('last7days', '7d') else
            'last30days'  if tf_key in ('last30days', '30d') else
            'lastmonth'   if tf_key in ('lastmonth', 'lastmonthhtml') else
            'lastyear'    if tf_key in ('lastyear', 'lastyearhtml') else
            'all'
        )

        end_dt = timezone.localtime(timezone.now())
        if tf == 'last24hours':
            start_dt = end_dt - timedelta(hours=24)
        elif tf == 'last7days':
            start_dt = end_dt - timedelta(days=7)
        elif tf == 'last30days':
            start_dt = end_dt - timedelta(days=30)
        elif tf == 'lastmonth':
            first_this_month = end_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end = first_this_month - timedelta(seconds=1)
            start_dt = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_dt = last_month_end
        elif tf == 'lastyear':
            start_dt = end_dt - timedelta(days=365)
        else:
            start_dt = None

        logs_qs = KeywordLog.objects.all()
        if start_dt:
            logs_qs = logs_qs.filter(updated_at__gte=start_dt, updated_at__lte=end_dt)
        logs_qs = logs_qs.order_by('-user_search_count')

        # Mirror user_search fuzzy
        STOPWORDS = {
            'the','or','at','and','of','to','a','an','in','on','by','for','with','from',
            'is','are','as','that','this','these','those','be','was','were','been','it',
            'its','into','than','then','over','under','between','among','via','per','vs'
        }

        def build_reference_vocab(row_limit=20000):
            vocab = set()
            for title, keywords in Books.objects.only('title', 'primary_keyword') \
                                               .values_list('title', 'primary_keyword')[:row_limit]:
                if title:
                    for w in title.replace(',', ' ').split():
                        wl = w.strip().lower()
                        if len(wl) >= 3 and wl not in STOPWORDS:
                            vocab.add(wl)
                if keywords:
                    for w in keywords.replace(',', ' ').split():
                        wl = w.strip().lower()
                        if len(wl) >= 3 and wl not in STOPWORDS:
                            vocab.add(wl)
            return list(vocab)

        REFERENCE_VOCAB = build_reference_vocab()

        def fuzzy_variants(token, n=7, cutoff=0.68):
            base = (token or "").lower().strip()
            if not base:
                return []
            matches = _difflib.get_close_matches(base, REFERENCE_VOCAB, n=n, cutoff=cutoff)
            if base not in matches:
                matches.insert(0, base)
            return matches

        def book_results_count_for_keyword(kw: str) -> int:
            kw = (kw or '').strip()
            if not kw or kw.lower() in STOPWORDS:
                return 0
            variants = fuzzy_variants(kw, n=7, cutoff=0.68) or [kw.lower()]
            q_or = Q()
            for v in variants:
                q_or |= (Q(title__icontains=v) | Q(author__icontains=v) | Q(primary_keyword__icontains=v))
            if not q_or:
                return 0
            return Books.objects.filter(q_or, is_archived=False).count()

        no_results_rows = []
        for log in logs_qs:
            kw = (getattr(log, 'user_keyword_search', '') or '').strip()
            # WRONG: cnt = compute_book_results_count_same_as_user(kw)
            cnt = book_results_count_for_keyword(kw)  # <-- use the helper you defined above
        
            if cnt == 0:
                first_s, last_s = _parse_first_last(getattr(log, "search_times", ""))
                if not first_s:
                    first_s = _fmt_dt_local(getattr(log, "created_at", None))
                if not last_s:
                    last_s = _fmt_dt_local(getattr(log, "updated_at", None))
                no_results_rows.append({
                    "keyword": kw,
                    "count": int(getattr(log, "user_search_count", 0) or 0),
                    "first": first_s or "—",
                    "last":  last_s or "—",
                })


        # Alphabetical by keyword (case-insensitive), empty last
        def _kw_sort_key(r):
            kw = str(r.get("keyword", ""))
            norm = unicodedata.normalize("NFKD", kw).strip().lower()
            return (norm == "", norm)
        no_results_rows.sort(key=_kw_sort_key)

    except Exception:
        no_results_rows = list(context.get("no_results_rows", []) or [])

    # Pull the same date range used in the charts for description
    _s = stats.get("start_date", "—")
    _e = stats.get("end_date", "—")

    if not no_results_rows:
        flowables.append(Paragraph("No keywords without results for the selected period.", content_style))
        flowables.append(Spacer(1, 10))
        desc3 = (
            "This page highlights keywords that returned no book results in the selected period "
            f"from {_s} to {_e}. None were found. Use this signal to confirm that patrons are "
            "generally finding what they need, and continue monitoring to catch new unmet searches early."
        )
        flowables.append(Paragraph(desc3, content_style))
    else:
        # Styles for the table
        header_cell_style = ParagraphStyle(
            name='HeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            alignment=1,
            textColor=colors.white,
        )
        body_keyword_style = ParagraphStyle(
            name='BodyKeyword',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            wordWrap='CJK'
        )
        body_center_style = ParagraphStyle(
            name='BodyCenter',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            alignment=1
        )

        header_row = [
            Paragraph("Keyword", header_cell_style),
            Paragraph("Amount of<br/>Times Searched", header_cell_style),
            Paragraph("First Searched", header_cell_style),
            Paragraph("Last Searched", header_cell_style),
        ]

        tdata = [header_row]
        for row in no_results_rows:
            tdata.append([
                Paragraph(str(row.get("keyword", "")), body_keyword_style),
                Paragraph(str(int(row.get("count", 0))), body_center_style),
                Paragraph(str(row.get("first", "—")), body_center_style),
                Paragraph(str(row.get("last", "—")),  body_center_style),
            ])

        table = Table(
            tdata,
            colWidths=[3.0*inch, 1.1*inch, 1.2*inch, 1.2*inch],
            repeatRows=1
        )
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3e151a')),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, 0), 9),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING',(0,0),(-1,0), 8),

            # Body styling
            ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE',   (0, 1), (-1, -1), 10),
            ('VALIGN',     (0, 1), (-1, -1), 'TOP'),
            ('ALIGN',      (1, 1), (1, -1), 'CENTER'),
            ('ALIGN',      (2, 1), (3, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.HexColor('#f8f8f8')]),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('LEFTPADDING',(0, 0), (-1, -1), 6),
            ('RIGHTPADDING',(0,0), (-1,-1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING',(0,1),(-1,-1), 6),

            # Ensure header text white (kept last for precedence)
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ]))
        flowables.append(table)

        # Description + italic note
        flowables.append(Spacer(1, 10))
        desc3_main = (
            "This table surfaces keywords that returned no book results in the selected period "
            f"from <b>{_s}</b> to <b>{_e}</b>. Use it to understand what students are searching for but cannot find. "
            "Treat these entries as an actionable recommendations list for acquisitions and/or metadata improvements."
        )
        flowables.append(Paragraph(desc3_main, content_style))
        flowables.append(Spacer(1, 6))
        desc3_note = (
            "<i>Note: misspellings and variations are recorded exactly as entered and are still counted "
            "as keywords by the system.</i>"
        )
        flowables.append(Paragraph(desc3_note, content_style))

    # ---- Build ----
    doc.build(flowables, onFirstPage=create_header_and_footer, onLaterPages=create_header_and_footer)

    # ---- Cleanup ----
    for p in (locals().get('img_path1'), locals().get('img_path2')):
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


