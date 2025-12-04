import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# Function to preprocess the Form 4 data from CSV
def preprocess_form_4_data(csv_file):
    # Load the CSV data into a Pandas DataFrame
    df = pd.read_csv(csv_file)

    # Remove rows where required columns are missing or contain 'N/A'
    df = df.dropna(subset=['Title', 'Transaction Date', 'Acquired_Disposed', 'Amount', 'Price'])
    df = df[df['Price'] != 'N/A']
    
    # Clean 'Amount' by removing commas and converting to integer
    df['Amount'] = df['Amount'].replace({',': ''}, regex=True).astype(int)  # Remove commas and convert to int
    
    # Convert 'Transaction Date' to datetime
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], format='%m/%d/%Y')

    # Clean 'Price' by removing non-numeric characters like "$" and "(2)" and convert to float
    df['Price'] = df['Price'].replace(
    {r'\(': '-', r'\)': '', r',': '', r'\$': ''},
    regex=True
)

    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')

    # Filter the data based on 'Acquired_Disposed' column (A = Acquired, D = Disposed)
    df['Acquired_Disposed'] = df['Acquired_Disposed'].apply(lambda x: 'Acquired' if x == 'A' else 'Disposed')

    return df

# Function to generate a stock plot for acquired vs disposed
def generate_stock_plot(df):
    # Group by transaction date and Acquired/Disposed status
    df_grouped = df.groupby(['Transaction Date', 'Acquired_Disposed']).agg(
        total_amount=('Amount', 'sum'),
        average_price=('Price', 'mean')
    ).reset_index()

    # Plotting the data
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Bar plot for total amount
    ax1.bar(df_grouped[df_grouped['Acquired_Disposed'] == 'Acquired']['Transaction Date'],
            df_grouped[df_grouped['Acquired_Disposed'] == 'Acquired']['total_amount'], color='green', label='Acquired', alpha=0.6)
    ax1.bar(df_grouped[df_grouped['Acquired_Disposed'] == 'Disposed']['Transaction Date'],
            df_grouped[df_grouped['Acquired_Disposed'] == 'Disposed']['total_amount'], color='red', label='Disposed', alpha=0.6)

    # Labels and title
    ax1.set_xlabel('Transaction Date')
    ax1.set_ylabel('Total Amount')
    ax1.set_title('Acquired vs Disposed Amounts Over Time')
    ax1.legend()
    plt.xticks(rotation=45)
    plt.savefig('static/img/finalgraph.png')
    plt.close(fig)

# Function to generate a stock analysis report
def generate_stock_analysis(df):
    # Basic summary statistics
    summary = df.describe()

    # Calculate total acquired and disposed amount
    total_acquired = df[df['Acquired_Disposed'] == 'Acquired']['Amount'].sum()
    total_disposed = df[df['Acquired_Disposed'] == 'Disposed']['Amount'].sum()

    # Calculate the average price of acquisitions and disposals
    avg_acquired_price = df[df['Acquired_Disposed'] == 'Acquired']['Price'].mean()
    avg_disposed_price = df[df['Acquired_Disposed'] == 'Disposed']['Price'].mean()

    # Print the analysis report
    print("Stock Analysis Report:")
    print(f"Total Acquired Amount: {total_acquired}")
    print(f"Total Disposed Amount: {total_disposed}")
    print(f"Average Acquired Price: ${avg_acquired_price:.2f}")
    print(f"Average Disposed Price: ${avg_disposed_price:.2f}")

    # Output DataFrame summary statistics
    print("\nSummary Statistics:")
    print(summary)

# Example usage: Preprocess the data and generate plots
if __name__ == "__main__":
    # Path to the form_4_filings.csv file
    csv_file = 'form_4_filings.csv'
    
    # Preprocess the data
    df = preprocess_form_4_data(csv_file)
    
    # Generate the stock plot
    generate_stock_plot(df)
    
    # Generate the stock analysis report
    generate_stock_analysis(df)
