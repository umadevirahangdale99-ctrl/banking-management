from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
except ImportError as exc:
    REPORTLAB_IMPORT_ERROR = exc
else:
    REPORTLAB_IMPORT_ERROR = None


class BankStatement:
    """Generate bank statements in PDF format"""
    
    def __init__(self, account, bank_name="Banking Management System"):
        if REPORTLAB_IMPORT_ERROR:
            raise ImportError(
                "ReportLab is required to generate PDF statements. "
                "Install it with: pip install reportlab"
            ) from REPORTLAB_IMPORT_ERROR

        self.account = account
        self.bank_name = bank_name
        self.styles = getSampleStyleSheet()

    def _transaction_value(self, transaction, key, default=None):
        if isinstance(transaction, dict):
            return transaction.get(key, default)
        if key == "type":
            return getattr(transaction, "transaction_type", default)
        return getattr(transaction, key, default)

    def _transaction_date(self, transaction):
        raw_date = self._transaction_value(transaction, "date", "")
        for date_format in ("%d-%m-%Y,%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(raw_date, date_format)
            except (TypeError, ValueError):
                continue
        return None

    def _is_deposit(self, transaction_type):
        return transaction_type in ("Deposit", "Deposite", "Transfer In")

    def _is_withdrawal(self, transaction_type):
        return transaction_type in (
            "Withdraw",
            "Transfer Out",
            "QR Payment",
            "UPI Payment",
            "Bill Payment",
            "Recharge",
            "Credit Card Payment",
            "Fixed Deposit Opened",
            "RD Installment",
        )
        
    def generate_pdf(self, filename, start_date=None, end_date=None):
        """Generate PDF statement and save to file"""
        
        # Filter transactions by date range
        transactions = self.account.transactions
        if start_date and end_date:
            filtered_transactions = []
            for t in transactions:
                trans_datetime = self._transaction_date(t)
                if trans_datetime and start_date <= trans_datetime.date() <= end_date:
                    filtered_transactions.append(t)
            transactions = filtered_transactions
        
        # Create PDF
        pdf = SimpleDocTemplate(filename, pagesize=letter)
        elements = []
        
        # Add header
        elements.extend(self._create_header())
        elements.append(Spacer(1, 0.3*inch))
        
        # Add account details
        elements.extend(self._create_account_details())
        elements.append(Spacer(1, 0.2*inch))
        
        # Add transaction table
        elements.extend(self._create_transaction_table(transactions, start_date, end_date))
        elements.append(Spacer(1, 0.3*inch))
        
        # Add summary
        elements.extend(self._create_summary())
        elements.append(Spacer(1, 0.2*inch))
        
        # Add footer
        elements.extend(self._create_footer())
        
        # Build PDF
        pdf.build(elements)
        return filename

    def _create_header(self):
        """Create PDF header with bank details"""
        elements = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0b2545'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph(self.bank_name, title_style))
        
        # Subtitle
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#536a8a'),
            alignment=TA_CENTER
        )
        elements.append(Paragraph("Account Statement", subtitle_style))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
        
        return elements

    def _create_account_details(self):
        """Create account details section"""
        elements = []
        
        detail_style = ParagraphStyle(
            'DetailStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#0b2545'),
            fontName='Helvetica'
        )
        
        account_info = f"""
        <b>Account Number:</b> {self.account.account_no}<br/>
        <b>Account Holder:</b> {self.account.name}<br/>
        <b>Current Balance:</b> ${self.account.get_balance():,.2f}<br/>
        <b>Statement Period:</b> {datetime.now().strftime('%B %Y')}
        """
        
        elements.append(Paragraph(account_info, detail_style))
        
        return elements

    def _create_transaction_table(self, transactions, start_date, end_date):
        """Create transactions table"""
        elements = []
        
        # Table title
        table_title_style = ParagraphStyle(
            'TableTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#0b2545'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph("Transaction Details", table_title_style))
        
        # Prepare table data
        table_data = [['Date', 'Type', 'Amount', 'Balance']]
        
        if transactions:
            running_balance = self.account.get_balance() - sum(
                (
                    -self._transaction_value(t, "amount", 0)
                    if self._is_withdrawal(self._transaction_value(t, "type"))
                    else self._transaction_value(t, "amount", 0)
                )
                for t in transactions
            )
            
            for transaction in transactions:
                trans_type = self._transaction_value(transaction, "type", "Unknown")
                trans_amount = self._transaction_value(transaction, "amount", 0)
                trans_date = self._transaction_value(transaction, "date", "")
                
                if self._is_deposit(trans_type):
                    running_balance += trans_amount
                elif self._is_withdrawal(trans_type):
                    running_balance -= trans_amount
                
                table_data.append([
                    trans_date[:10],  # Date only
                    trans_type,
                    f"${trans_amount:,.2f}",
                    f"${running_balance:,.2f}"
                ])
        else:
            table_data.append(['No transactions', '', '', ''])
        
        # Create table
        table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0b2545')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dce8fb')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f8ff')]),
        ]))
        
        elements.append(table)
        return elements

    def _create_summary(self):
        """Create transaction summary"""
        elements = []
        
        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#0b2545'),
            fontName='Helvetica-Bold'
        )
        
        # Calculate totals
        total_deposits = sum(
            (
                    self._transaction_value(t, "amount", 0)
                    if self._is_deposit(self._transaction_value(t, "type"))
                    else 0
            )
            for t in self.account.transactions
        )
        total_withdrawals = sum(
            (
                    self._transaction_value(t, "amount", 0)
                    if self._is_withdrawal(self._transaction_value(t, "type"))
                    else 0
            )
            for t in self.account.transactions
        )
        
        summary_text = f"""
        <b>Transaction Summary:</b><br/>
        Total Deposits: ${total_deposits:,.2f}<br/>
        Total Withdrawals: ${total_withdrawals:,.2f}<br/>
        Net Change: ${total_deposits - total_withdrawals:,.2f}<br/>
        """
        
        elements.append(Paragraph(summary_text, summary_style))
        
        return elements

    def _create_footer(self):
        """Create PDF footer"""
        elements = []
        
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#536a8a'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        footer_text = """
        This is a computer-generated statement and does not require a signature.<br/>
        For any queries, please contact our customer support.<br/>
        <b>Banking Management System</b>
        """
        
        elements.append(Paragraph(footer_text, footer_style))
        
        return elements
