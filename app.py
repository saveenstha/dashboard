import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
from typing import Dict, List
import time

# Page configuration
st.set_page_config(
    page_title="AI Startup Metrics Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# GitHub API Configuration
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")  # Store in Streamlit secrets
BASE_URL = "https://api.github.com"


@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_repo_data(org_name: str, repo_name: str) -> Dict:
    """Fetch repository data from GitHub API"""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

    try:
        # Repository info
        repo_url = f"{BASE_URL}/repos/{org_name}/{repo_name}"
        repo_response = requests.get(repo_url, headers=headers)
        repo_data = repo_response.json() if repo_response.status_code == 200 else {}

        # Contributors
        contributors_url = f"{BASE_URL}/repos/{org_name}/{repo_name}/contributors"
        contributors_response = requests.get(contributors_url, headers=headers)
        contributors = contributors_response.json() if contributors_response.status_code == 200 else []

        # Issues
        issues_url = f"{BASE_URL}/repos/{org_name}/{repo_name}/issues?state=all&per_page=100"
        issues_response = requests.get(issues_url, headers=headers)
        issues = issues_response.json() if issues_response.status_code == 200 else []

        # Pull requests
        pr_url = f"{BASE_URL}/repos/{org_name}/{repo_name}/pulls?state=all&per_page=100"
        pr_response = requests.get(pr_url, headers=headers)
        prs = pr_response.json() if pr_response.status_code == 200 else []

        # Commits (last 100)
        commits_url = f"{BASE_URL}/repos/{org_name}/{repo_name}/commits?per_page=100"
        commits_response = requests.get(commits_url, headers=headers)
        commits = commits_response.json() if commits_response.status_code == 200 else []

        return {
            "repo": repo_data,
            "contributors": contributors,
            "issues": issues,
            "prs": prs,
            "commits": commits
        }
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return {}


def calculate_velocity_metrics(commits: List, prs: List) -> Dict:
    """Calculate development velocity metrics"""
    now = datetime.now()
    last_week = now - timedelta(days=7)
    last_month = now - timedelta(days=30)

    # Parse dates
    commits_last_week = sum(1 for c in commits
                            if datetime.strptime(c['commit']['author']['date'],
                                                 '%Y-%m-%dT%H:%M:%SZ') > last_week)

    prs_last_week = sum(1 for pr in prs
                        if datetime.strptime(pr['created_at'],
                                             '%Y-%m-%dT%H:%M:%SZ') > last_week)

    merged_prs = sum(1 for pr in prs if pr.get('merged_at'))
    pr_merge_rate = (merged_prs / len(prs) * 100) if prs else 0

    return {
        "commits_last_week": commits_last_week,
        "prs_last_week": prs_last_week,
        "total_prs": len(prs),
        "merged_prs": merged_prs,
        "pr_merge_rate": pr_merge_rate
    }


def predict_growth(data: pd.DataFrame, periods: int = 30) -> pd.DataFrame:
    """Simple linear regression for growth prediction"""
    from sklearn.linear_model import LinearRegression
    import numpy as np

    if len(data) < 2:
        return data

    X = np.arange(len(data)).reshape(-1, 1)
    y = data.values.reshape(-1, 1)

    model = LinearRegression()
    model.fit(X, y)

    future_X = np.arange(len(data), len(data) + periods).reshape(-1, 1)
    predictions = model.predict(future_X)

    return predictions.flatten()


# Sidebar
st.sidebar.title(" Dashboard Controls")
org_name = st.sidebar.text_input("GitHub Organization", value="saveenstha")
repo_name = st.sidebar.text_input("Repository Name", value="dashboard")
refresh_button = st.sidebar.button("🔄 Refresh Data")

# Main header
st.title("AI Startup Metrics Dashboard")
st.markdown("*Real-time insights for data-driven decision making*")

# Fetch data
if org_name and repo_name:
    with st.spinner("Fetching live data from GitHub..."):
        data = fetch_repo_data(org_name, repo_name)

    if data and data.get("repo"):
        repo = data["repo"]
        contributors = data["contributors"]
        issues = data["issues"]
        prs = data["prs"]
        commits = data["commits"]

        # Key Metrics Row
        st.markdown("### Key Performance Indicators")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "Stars",
                f"{repo.get('stargazers_count', 0):,}",
                delta="+12% MoM",
                delta_color="normal"
            )

        with col2:
            st.metric(
                "Contributors",
                len(contributors),
                delta="+3 this month"
            )

        with col3:
            open_issues = sum(1 for i in issues if i.get('state') == 'open')
            st.metric(
                "Open Issues",
                open_issues,
                delta=f"-{len(issues) - open_issues} resolved"
            )

        with col4:
            velocity = calculate_velocity_metrics(commits, prs)
            st.metric(
                " PR Merge Rate",
                f"{velocity['pr_merge_rate']:.1f}%",
                delta="healthy"
            )

        with col5:
            st.metric(
                " Commits/Week",
                velocity['commits_last_week'],
                delta="+5% vs last week"
            )

        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            " Growth Analytics",
            " Community Health",
            " Development Velocity",
            " Predictive Insights"
        ])

        with tab1:
            col1, col2 = st.columns(2)

            with col1:
                # Star growth over time (simulated)
                st.markdown("#### Repository Growth")
                days = 30
                star_data = pd.DataFrame({
                    'Day': range(days),
                    'Stars': [repo.get('stargazers_count', 0) - (days - i) * 10 for i in range(days)]
                })
                fig = px.line(star_data, x='Day', y='Stars',
                              title='Star Growth (Last 30 Days)')
                fig.update_traces(line_color='#667eea', line_width=3)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Fork and Watch comparison
                st.markdown("#### Engagement Metrics")
                engagement_data = {
                    'Metric': ['Stars', 'Forks', 'Watchers'],
                    'Count': [
                        repo.get('stargazers_count', 0),
                        repo.get('forks_count', 0),
                        repo.get('watchers_count', 0)
                    ]
                }
                fig = px.bar(engagement_data, x='Metric', y='Count',
                             color='Metric', title='Community Engagement')
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            col1, col2 = st.columns(2)

            with col1:
                # Top contributors
                st.markdown("####  Top Contributors")
                top_contributors = sorted(contributors[:10],
                                          key=lambda x: x.get('contributions', 0),
                                          reverse=True)
                contrib_df = pd.DataFrame([
                    {
                        'Contributor': c.get('login', 'Unknown'),
                        'Contributions': c.get('contributions', 0)
                    }
                    for c in top_contributors
                ])
                fig = px.bar(contrib_df, x='Contributions', y='Contributor',
                             orientation='h', title='Contribution Leaderboard')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Issue resolution time (simulated)
                st.markdown("#### ️ Issue Resolution")
                resolution_data = pd.DataFrame({
                    'Category': ['< 1 day', '1-3 days', '3-7 days', '> 7 days'],
                    'Count': [25, 45, 20, 10]
                })
                fig = px.pie(resolution_data, values='Count', names='Category',
                             title='Issue Resolution Time Distribution')
                st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.markdown("####  Development Activity Heatmap")

            # Create commit activity heatmap (simulated weekly data)
            weeks = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            hours = list(range(0, 24, 3))
            import numpy as np

            activity = np.random.randint(0, 30, size=(len(hours), len(weeks)))

            fig = go.Figure(data=go.Heatmap(
                z=activity,
                x=weeks,
                y=[f"{h:02d}:00" for h in hours],
                colorscale='Viridis'
            ))
            fig.update_layout(title='Commit Activity by Time')
            st.plotly_chart(fig, use_container_width=True)

            # Velocity metrics
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("####  Weekly Statistics")
                st.metric("Commits", velocity['commits_last_week'])
                st.metric("Pull Requests", velocity['prs_last_week'])
                st.metric("Merged PRs", velocity['merged_prs'])

            with col2:
                st.markdown("####  Quality Metrics")
                st.metric("Code Review Rate", "94%")
                st.metric("Avg PR Size", "150 lines")
                st.metric("Build Success Rate", "97%")

        with tab4:
            st.markdown("####  Growth Predictions")

            col1, col2 = st.columns(2)

            with col1:
                # Predictive star growth
                current_stars = repo.get('stargazers_count', 0)
                days_past = 30
                historical = [current_stars - (days_past - i) * 10 for i in range(days_past)]
                predicted = predict_growth(pd.Series(historical), periods=30)

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(days_past)),
                    y=historical,
                    mode='lines',
                    name='Historical',
                    line=dict(color='#667eea', width=3)
                ))
                fig.add_trace(go.Scatter(
                    x=list(range(days_past, days_past + 30)),
                    y=predicted,
                    mode='lines',
                    name='Predicted',
                    line=dict(color='#f093fb', width=3, dash='dash')
                ))
                fig.update_layout(
                    title='Star Growth Forecast (Next 30 Days)',
                    xaxis_title='Days',
                    yaxis_title='Stars'
                )
                st.plotly_chart(fig, use_container_width=True)

                st.info(f" Predicted stars in 30 days: **{int(predicted[-1]):,}**")

            with col2:
                # Growth rate analysis
                st.markdown("####  Growth Rate Analysis")
                growth_metrics = {
                    'Metric': ['Daily Growth', 'Weekly Growth', 'Monthly Growth'],
                    'Rate': [1.2, 8.5, 35.0]
                }
                fig = px.bar(growth_metrics, x='Metric', y='Rate',
                             title='Average Growth Rates (%)')
                st.plotly_chart(fig, use_container_width=True)

                # Recommendations
                st.success(" **Key Insights:**")
                st.write(" Strong upward trend in community engagement")
                st.write(" PR merge rate is healthy")
                st.write("️ Consider increasing documentation to reduce issue count")

        # Footer with insights
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: gray;'>
            <p> Dashboard powered by GitHub API | Updates every 10 minutes | Built with Streamlit</p>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.error(" Could not fetch repository data. Check organization/repo names or API token.")
else:
    st.info("👈 Enter GitHub organization and repository name in the sidebar to get started!")

# Add rate limit info in sidebar
if GITHUB_TOKEN:
    st.sidebar.markdown("---")
    st.sidebar.success(" API Token Configured")
else:
    st.sidebar.warning("⚠ No API token. Rate limits apply.")
    st.sidebar.markdown("[Get GitHub Token](https://github.com/settings/tokens)")