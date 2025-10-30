import streamlit as st
import pandas as pd
import numpy as np
import io

# Set the page configuration for a professional title
st.set_page_config(
    page_title="Shopify Inventory Converter",
    layout="centered"
)

# --- CORE TRANSFORMATION FUNCTION ---
def convert_to_shopify_format(df):
    """
    Takes the wide format master DataFrame and converts it to the long Shopify format.
    """
    # Identify size columns and OTS inventory columns
    size_cols = [f'Size {i}' for i in range(1, 9)]
    ots_cols = [f'ots{i}' for i in range(1, 9)]

    # Select core columns and handle missing columns gracefully
    df_core = df[['Style major', 'Color'] + [col for col in size_cols if col in df.columns] + [col for col in ots_cols if col in df.columns]].copy()
    df_core['Color'] = df_core['Color'].fillna('').astype(str)

    # Melt 1: Unpivot the size labels
    df_sizes = pd.melt(
        df_core,
        id_vars=['Style major', 'Color'],
        value_vars=[col for col in size_cols if col in df_core.columns],
        var_name='Size_Col_Name',
        value_name='Option2 Value'
    )

    # Melt 2: Unpivot the inventory quantities
    df_ots = pd.melt(
        df_core,
        id_vars=['Style major', 'Color'],
        value_vars=[col for col in ots_cols if col in df_core.columns],
        var_name='OTS_Col_Name',
        value_name='New York Showroom'
    )

    # Create a key to merge on (extract the number 1 through 8)
    df_sizes['Key'] = df_sizes['Size_Col_Name'].astype(str).str.split(' ').str[-1]
    df_ots['Key'] = df_ots['OTS_Col_Name'].astype(str).str[3]

    # Merge the two DataFrames
    df_combined = pd.merge(
        df_sizes, df_ots, on=['Style major', 'Color', 'Key'], how='inner'
    )
    
    # Clean and filter the result (inventory > 0 and valid size label)
    df_cleaned = df_combined[
        (pd.to_numeric(df_combined['New York Showroom'], errors='coerce').fillna(0) > 0) &
        (df_combined['Option2 Value'].astype(str).str.strip().str.len() > 0)
    ].copy()

    # Rename, add constant columns, and format
    df_cleaned.rename(columns={'Style major': 'Handle', 'Color': 'Option1 Value'}, inplace=True)
    df_cleaned['Option1 Name'] = 'Color'
    df_cleaned['Option2 Name'] = 'Size'
    df_cleaned['Option3 Name'] = np.nan
    df_cleaned['Option3 Value'] = np.nan
    df_cleaned['New York Showroom'] = pd.to_numeric(df_cleaned['New York Showroom'], errors='coerce').fillna(0).astype(int)

    # Final column reorder
    df_final = df_cleaned[[
        'Handle', 'Option1 Name', 'Option1 Value', 'Option2 Name',
        'Option2 Value', 'Option3 Name', 'Option3 Value', 'New York Showroom'
    ]].reset_index(drop=True)
    
    return df_final

# --- STREAMLIT GUI INTERFACE ---

st.title("🛍️ Shopify Inventory Converter")
st.markdown("Upload your raw, wide-format master CSV file. The tool will convert it to the Shopify-compatible variant format, filtering for positive inventory, and provide a clean CSV download.")

uploaded_file = st.file_uploader(
    "1. Upload Your RAW Master CSV File (.csv)",
    type="csv"
)

if uploaded_file is not None:
    try:
        data = pd.read_csv(uploaded_file)
        
        # Quick check for minimum required column headers
        required_cols = ['Style major', 'Color', 'Size 1', 'ots1']
        if not all(col in data.columns for col in required_cols):
            st.error("Error: The uploaded file is missing critical columns (e.g., 'Style major', 'Color', 'Size 1', 'ots1'). Please check the file.")
        else:
            # Run the core conversion function
            with st.spinner('2. Converting to Shopify Format...'):
                df_clean = convert_to_shopify_format(data)
            
            # Prepare the download button
            csv_output = df_clean.to_csv(index=False).encode('utf-8')
            output_filename = uploaded_file.name.replace('.csv', '').replace('WEB OTS', 'Shopify_Cleaned').strip() + ".csv"
            
            st.header("✅ Conversion Complete!")
            st.markdown(f"The file contains **{len(df_clean):,}** final product variants ready for Shopify.")
            
            st.download_button(
                label="3. Download Shopify Inventory CSV",
                data=csv_output,
                file_name=output_filename,
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"An unexpected error occurred during processing: {e}")