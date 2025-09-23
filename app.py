import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import os
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import base64
from ingestion import ingest_contract
from analysis import analyze_clauses
from suggestions import generate_suggestions
from save_to_sheets import process_contract_data, save_to_google_sheets
from modifier import render_download_button

# ------------------------------
# Page Config
# ------------------------------
st.set_page_config(
    page_title="AI Contract Compliance Checker",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ------------------------------
# Custom CSS for Styling
# ------------------------------
def load_css():
    st.markdown("""
    <style>
    /* ========= Global Background ========= */
    .stApp {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); /* dark gradient */
        color: #f5f5f5 !important;
    }

    /* ========= Hero Section ========= */
    .hero-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 4rem 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        background-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/></pattern></defs><rect width="100%" height="100%" fill="url(%23grain)"/></svg>');
    }

    /* ========= Cards ========= */
    .metric-card, .chart-container {
        background: rgba(255, 255, 255, 0.08);
        color: #f5f5f5 !important;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        text-align: center;
        margin: 1rem 0;
    }

    .risk-high { border-left: 5px solid #ff4757; }
    .risk-medium { border-left: 5px solid #ffa726; }
    .risk-low { border-left: 5px solid #26a69a; }

    /* ========= Upload Section ========= */
    .upload-section {
        background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
        padding: 3rem 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 2rem 0;
    }

    /* ========= Tabs ========= */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #1e2a38;
        color: #f5f5f5 !important;
        border-radius: 10px 10px 0px 0px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #4cafef !important;
        color: white !important;
        font-weight: 600 !important;
    }

    /* ========= Processing Animation ========= */
    .processing-animation {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        border-radius: 15px;
        margin: 2rem 0;
        color: #333 !important;
    }

    /* ========= Ensure All Text is Visible ========= */
    h1, h2, h3, h4, h5, h6, p, div, span {
        color: #f5f5f5 !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ------------------------------
# Database Functions
# ------------------------------
DB_PATH = "contract_history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            timestamp TEXT,
            num_clauses INTEGER,
            num_high INTEGER,
            num_medium INTEGER,
            num_low INTEGER,
            sheet_name TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_history(filename, num_clauses, num_high, num_medium, num_low, sheet_name=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO history (filename, timestamp, num_clauses, num_high, num_medium, num_low, sheet_name) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (filename, ts, num_clauses, num_high, num_medium, num_low, sheet_name))
    conn.commit()
    conn.close()

def load_history():
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql("SELECT * FROM history ORDER BY id DESC", conn)

        # Ensure numeric columns are properly converted
        numeric_cols = ["num_clauses", "num_high", "num_medium", "num_low"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    except Exception as e:
        st.error(f"❌ Error loading history: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


# ------------------------------
# Initialize Session State
# ------------------------------
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None
if "df_results" not in st.session_state:
    st.session_state.df_results = None

# ------------------------------
# Load CSS
# ------------------------------
load_css()

# ------------------------------
# Navigation Tabs
# ------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Home", 
    "📤 Upload & Analyze", 
    "📊 Charts & Insights", 
    "📋 Detailed Results", 
    "📈 Company Dashboard"
])

# ------------------------------
# HOME PAGE
# ------------------------------
with tab1:
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 3rem; margin-bottom: 1rem;">📑 AI Contract Compliance Checker</h1>
        <p style="font-size: 1.2rem; margin-bottom: 2rem;">
            Transform your contract analysis with AI-powered risk detection and compliance checking
        </p>
        <p style="font-size: 1rem; opacity: 0.9;">
            Upload your contracts • Get instant risk analysis • Receive actionable suggestions
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🔍 Smart Analysis</h3>
            <p>Advanced AI models analyze your contracts for potential risks and compliance issues</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>📊 Visual Insights</h3>
            <p>Comprehensive charts and dashboards to understand your contract portfolio</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>💡 Actionable Suggestions</h3>
            <p>Get specific recommendations to improve contract terms and reduce risks</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🚀 Getting Started")
    st.markdown("""
    1. **Navigate to Upload & Analyze** - Upload your contract PDF
    2. **View Results** - Get instant risk assessment and analysis
    3. **Explore Charts** - Visualize risk distribution and patterns
    4. **Review Details** - Examine clause-by-clause analysis
    5. **Track Progress** - Monitor your contract portfolio in the dashboard
    """)

# ------------------------------
# UPLOAD & ANALYZE PAGE
# ------------------------------
with tab2:
    st.markdown("""
    <div class="upload-section">
        <h2>📤 Upload Your Contract</h2>
        <p>Select a PDF contract file to begin the AI-powered analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload your contract in PDF format for analysis"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            st.info(f"📄 File size: {uploaded_file.size / 1024:.1f} KB")
        
        with col2:
            if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name
                
                # Processing Animation
                st.markdown("""
                <div class="processing-animation">
                    <h3>🔄 Processing Your Contract</h3>
                    <p>Please wait while we analyze your document...</p>
                </div>
                """, unsafe_allow_html=True)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Extract clauses
                status_text.text("🔍 Extracting clauses...")
                progress_bar.progress(25)
                clauses = ingest_contract(tmp_path)
                
                # Step 2: Analyze clauses
                status_text.text("🧠 Analyzing risks...")
                progress_bar.progress(50)
                analysis_results = analyze_clauses(clauses)
                
                # Step 3: Generate suggestions
                status_text.text("💡 Generating suggestions...")
                progress_bar.progress(75)
                suggestions = generate_suggestions(analysis_results)
                
                # Step 4: Process data
                status_text.text("📊 Preparing results...")
                progress_bar.progress(100)
                combined_data = process_contract_data(clauses, analysis_results, suggestions)

                # Step 5: Provide download button for safe contract
                status_text.text("✅ Preparing modified contract...")
                try:
                    render_download_button(tmp_path,analysis_results)
                except Exception as e:
                    st.error(f"❌ Failed to generate modified contract: {e}")
                
                # Save to session state
                st.session_state.analysis_data = combined_data
                st.session_state.df_results = pd.DataFrame(combined_data)
                st.session_state.analysis_complete = True
                
                # Clean up
                os.unlink(tmp_path)
                progress_bar.empty()
                status_text.empty()
                
                st.success("✅ Analysis Complete!")
                st.balloons()
    
    # Display results if analysis is complete
    if st.session_state.analysis_complete and st.session_state.df_results is not None:
        df = st.session_state.df_results
        
        st.markdown("### 📊 Analysis Summary")
        
        # Summary metrics
        num_clauses = len(df)
        num_high = (df["Risk_Severity"] == "High").sum()
        num_medium = (df["Risk_Severity"] == "Medium").sum()
        num_low = (df["Risk_Severity"] == "Low").sum()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{num_clauses}</h3>
                <p>Total Clauses</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card risk-high">
                <h3>{num_high}</h3>
                <p>High Risk</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card risk-medium">
                <h3>{num_medium}</h3>
                <p>Medium Risk</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card risk-low">
                <h3>{num_low}</h3>
                <p>Low Risk</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick actions
        st.markdown("### 🎯 Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 View Charts", use_container_width=True):
                st.info("Navigate to the 'Charts & Insights' tab to view visualizations")
        
        with col2:
            if st.button("📋 View Details", use_container_width=True):
                st.info("Navigate to the 'Detailed Results' tab for full analysis")
        
        with col3:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download CSV",
                csv,
                file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Save to history
        if uploaded_file:
            save_history(uploaded_file.name, num_clauses, num_high, num_medium, num_low)

# ------------------------------
# CHARTS & INSIGHTS PAGE (FIXED)
# ------------------------------
with tab3:
    st.markdown("# 📊 Charts & Insights")
    
    if not st.session_state.analysis_complete or st.session_state.df_results is None:
        st.warning("⚠️ No analysis data available. Please upload and analyze a contract first.")
    else:
        df = st.session_state.df_results.copy()
        
        # Ensure we have risk severity data
        if "Risk_Severity" not in df.columns or df.empty:
            st.error("⚠️ No risk analysis data available in the current contract.")
        else:
            # Clean and validate risk severity data
            df = df.dropna(subset=['Risk_Severity'])
            df['Risk_Severity'] = df['Risk_Severity'].astype(str).str.strip()
            
            if df.empty or df['Risk_Severity'].value_counts().sum() == 0:
                st.info("ℹ️ No risk classifications found in the analyzed contract.")
            else:
                # Set up matplotlib style for better appearance
                plt.style.use('default')
                sns.set_palette("husl")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("🎯 Risk Distribution")
                    
                    # Create properly sized figure
                    fig, ax = plt.subplots(figsize=(8, 5))
                    risk_counts = df["Risk_Severity"].value_counts()
                    
                    # Define colors for different risk levels
                    color_map = {'High': '#ff4757', 'Medium': '#ffa726', 'Low': '#26a69a'}
                    colors = [color_map.get(risk, '#74b9ff') for risk in risk_counts.index]
                    
                    bars = ax.bar(risk_counts.index, risk_counts.values, color=colors, alpha=0.8)
                    
                    # Add value labels on top of bars
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                               f'{int(height)}', ha='center', va='bottom', fontsize=12, fontweight='bold')
                    
                    ax.set_xlabel("Risk Severity", fontsize=12)
                    ax.set_ylabel("Number of Clauses", fontsize=12)
                    ax.set_title("Risk Distribution by Severity", fontsize=14, fontweight='bold', pad=20)
                    
                    # Set y-axis limits properly
                    max_value = risk_counts.max()
                    ax.set_ylim(0, max_value * 1.3)
                    
                    # Style improvements
                    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    
                    plt.tight_layout()
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)  # Close figure to free memory
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("📈 Risk Percentage")
                    
                    fig2, ax2 = plt.subplots(figsize=(8, 5))
                    risk_counts = df["Risk_Severity"].value_counts()
                    
                    # Define colors for pie chart
                    color_map = {'High': '#ff4757', 'Medium': '#ffa726', 'Low': '#26a69a'}
                    colors = [color_map.get(risk, '#74b9ff') for risk in risk_counts.index]
                    
                    # Create pie chart with better formatting
                    wedges, texts, autotexts = ax2.pie(
                        risk_counts.values,
                        labels=risk_counts.index,
                        autopct=lambda pct: f'{pct:.1f}%\n({int(pct*sum(risk_counts.values)/100)})',
                        colors=colors,
                        startangle=90,
                        explode=[0.05] * len(risk_counts)  # Slightly separate slices
                    )
                    
                    # Style improvements for text
                    plt.setp(autotexts, size=10, weight="bold", color='white')
                    plt.setp(texts, size=11, weight='bold')
                    
                    ax2.set_title("Risk Distribution Percentage", fontsize=14, fontweight='bold', pad=20)
                    
                    plt.tight_layout()
                    st.pyplot(fig2, use_container_width=True)
                    plt.close(fig2)  # Close figure to free memory
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Risk timeline (if timestamp available)
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.subheader("📅 Risk Analysis Trends")
                
                init_db()
                history_df = load_history()
                
                if not history_df.empty and len(history_df) > 1:
                    fig3, ax3 = plt.subplots(figsize=(14, 6))
                    
                    # Convert timestamp and sort
                    history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
                    history_df = history_df.sort_values('timestamp')
                    
                    # Plot trends with better styling
                    ax3.plot(history_df['timestamp'], history_df['num_high'], 'o-', 
                            color='#ff4757', label='High Risk', linewidth=3, markersize=8)
                    ax3.plot(history_df['timestamp'], history_df['num_medium'], 's-', 
                            color='#ffa726', label='Medium Risk', linewidth=3, markersize=8)
                    ax3.plot(history_df['timestamp'], history_df['num_low'], '^-', 
                            color='#26a69a', label='Low Risk', linewidth=3, markersize=8)
                    
                    ax3.set_xlabel("Date", fontsize=12)
                    ax3.set_ylabel("Number of Clauses", fontsize=12)
                    ax3.set_title("Risk Trends Over Time", fontsize=14, fontweight='bold', pad=20)
                    ax3.legend(fontsize=11, loc='upper left')
                    ax3.grid(True, alpha=0.3)
                    
                    # Format dates on x-axis
                    plt.xticks(rotation=45)
                    ax3.spines['top'].set_visible(False)
                    ax3.spines['right'].set_visible(False)
                    
                    plt.tight_layout()
                    st.pyplot(fig3, use_container_width=True)
                    plt.close(fig3)
                else:
                    st.info("📊 Need at least 2 analyses for trend visualization")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Additional analysis sections
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("🏷️ Risk Categories")
                    
                    if "Risk_Category" in df.columns and not df["Risk_Category"].isnull().all():
                        fig4, ax4 = plt.subplots(figsize=(10, 6))
                        category_counts = df["Risk_Category"].value_counts().head(8)
                        
                        bars = ax4.barh(range(len(category_counts)), category_counts.values, color='lightcoral', alpha=0.8)
                        ax4.set_yticks(range(len(category_counts)))
                        ax4.set_yticklabels(category_counts.index, fontsize=10)
                        ax4.set_xlabel("Number of Clauses", fontsize=12)
                        ax4.set_title("Top Risk Categories", fontsize=14, fontweight='bold', pad=20)
                        
                        # Add value labels
                        for i, bar in enumerate(bars):
                            width = bar.get_width()
                            ax4.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                                   f'{int(width)}', ha='left', va='center', fontweight='bold')
                        
                        ax4.grid(True, axis='x', alpha=0.3)
                        ax4.spines['top'].set_visible(False)
                        ax4.spines['right'].set_visible(False)
                        
                        plt.tight_layout()
                        st.pyplot(fig4, use_container_width=True)
                        plt.close(fig4)
                    else:
                        st.info("📋 Risk category data not available")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("📏 Clause Length Analysis")
                    
                    if "Clause_Text" in df.columns and not df["Clause_Text"].isnull().all():
                        df['clause_length'] = df['Clause_Text'].astype(str).str.len()
                        
                        fig5, ax5 = plt.subplots(figsize=(10, 6))
                        ax5.hist(df['clause_length'], bins=15, color='skyblue', alpha=0.7, edgecolor='black', linewidth=1.2)
                        ax5.set_xlabel("Clause Length (characters)", fontsize=12)
                        ax5.set_ylabel("Frequency", fontsize=12)
                        ax5.set_title("Distribution of Clause Lengths", fontsize=14, fontweight='bold', pad=20)
                        
                        # Add statistics
                        mean_length = df['clause_length'].mean()
                        ax5.axvline(mean_length, color='red', linestyle='--', linewidth=2, 
                                   label=f'Mean: {mean_length:.0f}')
                        ax5.legend()
                        
                        ax5.grid(True, alpha=0.3)
                        ax5.spines['top'].set_visible(False)
                        ax5.spines['right'].set_visible(False)
                        
                        plt.tight_layout()
                        st.pyplot(fig5, use_container_width=True)
                        plt.close(fig5)
                    else:
                        st.info("📄 Clause text data not available")
                    
                    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------
# DETAILED RESULTS PAGE
# ------------------------------
with tab4:
    st.markdown("# 📋 Detailed Analysis Results")
    
    if not st.session_state.analysis_complete or st.session_state.df_results is None:
        st.warning("⚠️ No analysis data available. Please upload and analyze a contract first.")
    else:
        df = st.session_state.df_results
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            risk_filter = st.selectbox("Filter by Risk Level:", ["All"] + list(df["Risk_Severity"].unique()))
        
        with col2:
            if "Risk_Category" in df.columns:
                category_filter = st.selectbox("Filter by Category:", ["All"] + list(df["Risk_Category"].unique()))
            else:
                category_filter = "All"
        
        with col3:
            search_term = st.text_input("Search in clauses:", placeholder="Enter search term...")
        
        # Apply filters
        filtered_df = df.copy()
        
        if risk_filter != "All":
            filtered_df = filtered_df[filtered_df["Risk_Severity"] == risk_filter]
        
        if category_filter != "All" and "Risk_Category" in df.columns:
            filtered_df = filtered_df[filtered_df["Risk_Category"] == category_filter]
        
        if search_term:
            if "Clause_Text" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Clause_Text"].str.contains(search_term, case=False, na=False)]
        
        st.markdown(f"### Showing {len(filtered_df)} of {len(df)} clauses")
        
        # Results table with styling
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Export options
        st.markdown("### 📤 Export Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Filtered CSV",
                csv,
                file_name=f"filtered_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            if st.button("📊 Export to Excel", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                    filtered_df.to_excel(tmp_file.name, index=False)
                    with open(tmp_file.name, "rb") as f:
                        st.download_button(
                            "⬇️ Download Excel",
                            f.read(),
                            file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.ms-excel"
                        )
        
        with col3:
            if st.button("📄 Save to Google Sheets", use_container_width=True):
                try:
                    sheet_name = save_to_google_sheets(filtered_df.to_dict('records'))
                    st.success(f"✅ Saved to Google Sheets: {sheet_name}")
                except Exception as e:
                    st.error(f"❌ Failed to save: {str(e)}")

# ------------------------------
# COMPANY DASHBOARD PAGE (FIXED AND STREAMLINED)
# ------------------------------
with tab5:
    st.markdown("# 📈 Company Dashboard")
    
    init_db()
    history_df = load_history()
    
    if history_df.empty:
        st.info("📝 No contract analysis history available. Start by analyzing some contracts!")
    else:
        # Data validation and cleaning
        try:
            # Convert timestamp to datetime and handle errors
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp'], errors='coerce')
            
            # Remove entries with invalid timestamps
            history_df = history_df.dropna(subset=['timestamp'])
            
            # Ensure numeric columns are properly typed
            numeric_cols = ['num_clauses', 'num_high', 'num_medium', 'num_low']
            for col in numeric_cols:
                if col in history_df.columns:
                    history_df[col] = pd.to_numeric(history_df[col], errors='coerce').fillna(0).astype(int)
                else:
                    history_df[col] = 0
            
            # Remove duplicate entries based on filename and timestamp (fix double counting)
            history_df = history_df.drop_duplicates(subset=['filename', 'timestamp'], keep='last')
            
            # Only keep entries that have meaningful data
            history_df = history_df[
                (history_df['num_clauses'] > 0) |  # Has clauses OR
                (history_df[['num_high', 'num_medium', 'num_low']].sum(axis=1) > 0)  # Has risk data
            ]
            
            if history_df.empty:
                st.warning("⚠️ No valid contract data available. Please analyze some contracts with proper data.")
                st.stop()
                
        except Exception as e:
            st.error(f"❌ Error processing dashboard data: {str(e)}")
            st.stop()
        
        # Calculate correct statistics
        total_contracts = len(history_df)
        total_clauses = int(history_df['num_clauses'].sum())
        total_high_risk = int(history_df['num_high'].sum())
        total_medium_risk = int(history_df['num_medium'].sum())
        total_low_risk = int(history_df['num_low'].sum())
        total_risk_clauses = total_high_risk + total_medium_risk + total_low_risk
        
        # Calculate meaningful averages
        avg_clauses_per_contract = total_clauses / total_contracts if total_contracts > 0 else 0
        high_risk_contracts = int((history_df['num_high'] > 0).sum())
        
        # Main dashboard metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{total_contracts}</h3>
                <p>Total Contracts Analyzed</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{total_clauses}</h3>
                <p>Total Clauses Processed</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{avg_clauses_per_contract:.0f}</h3>
                <p>Avg Clauses per Contract</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card risk-high">
                <h3>{high_risk_contracts}</h3>
                <p>Contracts with High Risk</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Only show risk analysis if we have risk data
        if total_risk_clauses > 0:
            st.markdown("### 🎯 Risk Analysis Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card risk-high">
                    <h3>{total_high_risk}</h3>
                    <p>High Risk Clauses</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card risk-medium">
                    <h3>{total_medium_risk}</h3>
                    <p>Medium Risk Clauses</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card risk-low">
                    <h3>{total_low_risk}</h3>
                    <p>Low Risk Clauses</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                risk_percentage = (total_high_risk / total_risk_clauses * 100) if total_risk_clauses > 0 else 0
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{risk_percentage:.1f}%</h3>
                    <p>High Risk Rate</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Risk visualization - only if we have meaningful data
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.subheader("📊 Risk Distribution")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Bar chart for risk distribution
                fig, ax = plt.subplots(figsize=(10, 6))
                
                risk_data = [total_high_risk, total_medium_risk, total_low_risk]
                risk_labels = ['High Risk', 'Medium Risk', 'Low Risk']
                colors = ['#ff4757', '#ffa726', '#26a69a']
                
                bars = ax.bar(risk_labels, risk_data, color=colors, alpha=0.8)
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:  # Only show label if there's data
                        ax.text(bar.get_x() + bar.get_width()/2., height + max(risk_data)*0.01,
                               f'{int(height)}', ha='center', va='bottom', fontsize=12, fontweight='bold')
                
                ax.set_title("Total Risk Clauses", fontsize=14, fontweight='bold', pad=20)
                ax.set_ylabel("Number of Clauses", fontsize=12)
                ax.grid(True, axis='y', alpha=0.3)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                
                plt.tight_layout()
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            
            with col2:
                # Pie chart for risk percentage
                fig2, ax2 = plt.subplots(figsize=(8, 6))
                
                # Only include non-zero values in pie chart
                non_zero_data = [(label, value) for label, value in zip(risk_labels, risk_data) if value > 0]
                
                if non_zero_data:
                    labels, values = zip(*non_zero_data)
                    colors_filtered = [colors[risk_labels.index(label)] for label in labels]
                    
                    wedges, texts, autotexts = ax2.pie(values, labels=labels, autopct='%1.1f%%', 
                                                      colors=colors_filtered, startangle=90)
                    plt.setp(autotexts, size=10, weight="bold", color='white')
                    plt.setp(texts, size=11, weight='bold')
                    
                    ax2.set_title("Risk Distribution %", fontsize=14, fontweight='bold', pad=20)
                else:
                    ax2.text(0.5, 0.5, 'No Risk Data Available', ha='center', va='center', 
                            transform=ax2.transAxes, fontsize=14)
                    ax2.axis('off')
                
                plt.tight_layout()
                st.pyplot(fig2, use_container_width=True)
                plt.close(fig2)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Timeline analysis - only if multiple contracts
        if len(history_df) > 1:
            st.markdown("### 📈 Analysis Timeline")
            
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            
            # Sort data by timestamp
            history_df_sorted = history_df.sort_values('timestamp')
            
            fig, ax = plt.subplots(figsize=(14, 6))
            
            # Plot contract analysis over time
            dates = history_df_sorted['timestamp'].dt.date
            ax.plot(dates, history_df_sorted['num_clauses'], 'o-', 
                   color='steelblue', label='Total Clauses', linewidth=2, markersize=6)
            
            # Add risk trends only if we have risk data
            if total_risk_clauses > 0:
                ax.plot(dates, history_df_sorted['num_high'], 's-', 
                       color='#ff4757', label='High Risk', linewidth=2, markersize=6)
                ax.plot(dates, history_df_sorted['num_medium'], '^-', 
                       color='#ffa726', label='Medium Risk', linewidth=2, markersize=6)
                ax.plot(dates, history_df_sorted['num_low'], 'v-', 
                       color='#26a69a', label='Low Risk', linewidth=2, markersize=6)
            
            ax.set_xlabel("Analysis Date", fontsize=12)
            ax.set_ylabel("Number of Clauses", fontsize=12)
            ax.set_title("Contract Analysis Timeline", fontsize=14, fontweight='bold', pad=20)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            plt.xticks(rotation=45)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Contract history table - simplified
        st.markdown("### 📋 Recent Contract Analysis")
        
        # Format display dataframe
        display_df = history_df.copy()
        display_df['Analysis Date'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        display_df = display_df.rename(columns={
            'filename': 'Contract File',
            'num_clauses': 'Clauses',
            'num_high': 'High Risk',
            'num_medium': 'Medium Risk', 
            'num_low': 'Low Risk'
        })
        
        # Sort by most recent and show only relevant columns
        display_df = display_df.sort_values('timestamp', ascending=False)
        columns_to_show = ['Contract File', 'Analysis Date', 'Clauses']
        
        # Only add risk columns if we have risk data
        if total_risk_clauses > 0:
            columns_to_show.extend(['High Risk', 'Medium Risk', 'Low Risk'])
        
        st.dataframe(
            display_df[columns_to_show].head(10),  # Show only last 10 entries
            use_container_width=True,
            hide_index=True
        )
        
        # Export and management options
        st.markdown("### 📤 Data Management")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export current data
            export_df = display_df[columns_to_show]
            csv_data = export_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Export History",
                csv_data,
                file_name=f"contract_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Show database info
            st.info(f"📊 Database: {len(history_df)} valid entries")
        
        with col3:
            # Clear history with confirmation
            if st.button("🗑️ Clear History", type="secondary", use_container_width=True):
                st.warning("⚠️ This will permanently delete all analysis history!")
                if st.button("✅ Confirm Delete", type="secondary"):
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("DELETE FROM history")
                        conn.commit()
                        conn.close()
                        st.success("✅ History cleared!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
# ------------------------------
# Footer
# ------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; padding: 2rem;">
    <p>📑 AI Contract Compliance Checker | Built with Streamlit & AI</p>
    <p>Transform your contract analysis workflow with intelligent automation</p>
</div>
""", unsafe_allow_html=True)

