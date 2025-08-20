import os
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Análisis de Polio: Cobertura de Vacunación y Casos"

# For deployment
server = app.server

# Load and prepare data
def load_and_prepare_data():
    """Load and prepare all datasets for the dashboard"""
    
    # Load datasets
    df_polio = pd.read_csv("data/number-of-estimated-paralytic-polio-cases-by-world-region.csv")
    df_metadata = pd.read_csv("data/country_metadata.csv")
    df_pop = pd.read_csv('data/total_population.csv')
    df_vaccine = pd.read_csv('data/global-vaccination-coverage.csv')
    
    # Prepare metadata
    df_metadata.rename(columns={'Country Code': 'Code'}, inplace=True)
    
    # Prepare population data
    df_pop.rename(columns={'Country Code': 'Code'}, inplace=True)
    year_columns = [col for col in df_pop.columns if col.isdigit()]
    df_pop_long = pd.melt(
        df_pop, 
        id_vars=['Country Name', 'Code', 'Indicator Name', 'Indicator Code'],
        value_vars=year_columns,
        var_name='year',
        value_name='total_pop'
    )
    df_pop_long['year'] = df_pop_long['year'].astype(int)
    df_pop_subset = df_pop_long[['Code', 'year', 'total_pop']]
    df_metadata_subset = df_metadata[['Code', 'Region', 'IncomeGroup']]
    
    # Prepare main polio dataset
    df_polio_clean = df_polio.copy()
    df_polio_clean.rename(columns={
        'Entity': 'country',
        'Code': 'code',
        'Year': 'year',
        'Estimated number of paralytic polio cases using reported number of cases after polio free certification (WHO, 2018 and Tebbens et al., 2011)': 'num_cases'
    }, inplace=True)
    
    # Merge with metadata and population
    df_polio_clean = pd.merge(df_polio_clean, df_metadata[['Code', 'Region', 'IncomeGroup']], left_on='code', right_on='Code', how='left')
    df_polio_clean.drop('Code', axis=1, inplace=True)
    df_polio_clean.rename(columns={'Region': 'region', 'IncomeGroup': 'income_group'}, inplace=True)
    
    df_polio_clean = pd.merge(df_polio_clean, df_pop_subset, left_on=['code', 'year'], right_on=['Code', 'year'], how='left')
    df_polio_clean.drop('Code', axis=1, inplace=True)
    
    # Calculate cases per million
    df_polio_clean['cases_per_million'] = (df_polio_clean['num_cases'] / df_polio_clean['total_pop']) * 1000000
    
    # Prepare income group aggregation
    aggregations = {
        'cases_per_million': 'mean',
        'num_cases': 'sum',
        'total_pop': 'sum'
    }
    df_income_time = df_polio_clean.dropna(subset=['income_group']).groupby(['income_group', 'year']).agg(aggregations).reset_index()
    df_income_time['income_cases_per_million'] = (df_income_time['num_cases'] / df_income_time['total_pop']) * 1000000
    
    # Prepare vaccine data
    df_vaccine_subset = df_vaccine[['Entity', 'Year', 'Pol3 (% of one-year-olds immunized)']].copy()
    df_vaccine_subset.rename(columns={
        'Entity': 'country',
        'Year': 'year',
        'Pol3 (% of one-year-olds immunized)': 'pol3_immunization_rate'
    }, inplace=True)
    
    # Merge polio and vaccine data
    df_polio_vaccine = pd.merge(df_polio_clean, df_vaccine_subset, on=['country', 'year'], how='left')
    
    # Fill missing vaccination data with country means
    country_means = df_polio_vaccine.groupby('country')['pol3_immunization_rate'].mean()
    for country in df_polio_vaccine['country'].unique():
        country_mask = df_polio_vaccine['country'] == country
        country_nulls = df_polio_vaccine.loc[country_mask, 'pol3_immunization_rate'].isnull()
        
        if country_nulls.any() and country in country_means and not pd.isna(country_means[country]):
            df_polio_vaccine.loc[country_mask & country_nulls, 'pol3_immunization_rate'] = country_means[country]
    
    return df_income_time, df_polio_vaccine

# Load data
df_income_time, df_polio_vaccine = load_and_prepare_data()

def create_stacked_area_chart(df_income_time):
    """Create the stacked area chart for income groups over time"""
    
    # Prepare data for stacked area plot
    df_stacked = df_income_time.pivot(index='year', columns='income_group', values='income_cases_per_million')
    df_stacked = df_stacked.fillna(0)
    
    # Create figure
    fig_stacked_area = go.Figure()
    
    # Color mapping for consistency
    color_map = {
        'Lower middle income': '#162C3F',
        'Low income': '#2B6387',
        'Upper middle income': '#5EB2D5',
        'High income': '#A4D5EE'
    }
    
    # Order income groups by average cases (highest to lowest)
    income_group_averages = df_stacked.mean().sort_values(ascending=False)
    income_groups = income_group_averages.index.tolist()
    
    # Add stacked areas
    for i, income_group in enumerate(income_groups):
        fig_stacked_area.add_trace(go.Scatter(
            x=df_stacked.index,
            y=df_stacked[income_group],
            mode='lines',
            name=income_group,
            fill='tonexty' if i > 0 else 'tozeroy',
            line=dict(width=0.5, color=color_map.get(income_group, '#5EB2D5')),
            fillcolor=color_map.get(income_group, '#5EB2D5'),
            stackgroup='one',
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Año: %{x}<br>' +
                          'Casos por millón: %{y:.2f}<br>' +
                          '<extra></extra>'
        ))
    
    # Update layout
    fig_stacked_area.update_layout(
        title='Evolución de Casos de Polio per Cápita por Grupo de Ingresos (1980-2016)',
        xaxis_title='Año',
        yaxis_title='Casos por Millón de Habitantes',
        width=1600,
        height=750,
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bgcolor='rgba(255,255,255,0.8)',
            borderwidth=1
        ),
        title_x=0.5,
        font=dict(size=14),
        margin=dict(l=100, r=200, t=100, b=100)
    )
    
    # Customize axes
    fig_stacked_area.update_xaxes(
        showgrid=True,
        gridcolor='lightgray',
        linecolor='black',
        title_font_size=14,
        tickfont_size=12,
        range=[1980, 2016],
        dtick=5
    )
    
    fig_stacked_area.update_yaxes(
        showgrid=True,
        gridcolor='lightgray',
        linecolor='black',
        title_font_size=14,
        tickfont_size=12,
        rangemode='tozero'
    )
    
    return fig_stacked_area

def create_vaccination_map(df_polio_vaccine):
    """Create the animated choropleth map with scatter overlay"""
    
    # Prepare data for animation
    df_combined = df_polio_vaccine.dropna(subset=['pol3_immunization_rate', 'cases_per_million', 'code']).copy()
    df_combined = df_combined[df_combined['code'].str.len() == 3]
    
    # Create 3-year periods
    df_combined['year_group'] = ((df_combined['year'] - 1980) // 3) * 3 + 1980
    df_combined['period_label'] = df_combined['year_group'].astype(str) + '-' + (df_combined['year_group'] + 2).astype(str)
    
    # Group by country and period
    df_combined_grouped = df_combined.groupby(['country', 'code', 'year_group', 'period_label', 'income_group']).agg({
        'pol3_immunization_rate': 'mean',
        'cases_per_million': 'mean',
        'total_pop': 'mean'
    }).reset_index()
    
    df_combined_grouped = df_combined_grouped.sort_values('year_group').reset_index(drop=True)
    
    # Create vaccination categories
    def get_vaccination_category(coverage):
        if coverage >= 95:
            return "Muy Alta (≥95%)"
        elif coverage >= 85:
            return "Alta (85-94%)"
        elif coverage >= 70:
            return "Media (70-84%)"
        elif coverage >= 50:
            return "Baja (50-69%)"
        else:
            return "Muy Baja (<50%)"
    
    df_combined_grouped['vaccination_category'] = df_combined_grouped['pol3_immunization_rate'].apply(get_vaccination_category)
    
    # Create bubble sizes
    df_combined_grouped['bubble_size'] = np.where(
        df_combined_grouped['cases_per_million'] > 0,
        np.sqrt(df_combined_grouped['cases_per_million']) * 8 + 5,
        3
    )
    df_combined_grouped['bubble_size'] = np.clip(df_combined_grouped['bubble_size'], 3, 40)
    
    # Country coordinates (simplified set)
    country_coords = {
        'Afghanistan': [33.0, 65.0], 'Algeria': [28.0, 3.0], 'Angola': [-12.0, 18.5],
        'Argentina': [-34.0, -64.0], 'Australia': [-25.0, 133.0], 'Bangladesh': [24.0, 90.0],
        'Brazil': [-14.0, -51.0], 'Canada': [60.0, -95.0], 'Chad': [15.0, 19.0],
        'Chile': [-30.0, -71.0], 'China': [35.0, 105.0], 'Colombia': [4.0, -72.0],
        'Congo': [-1.0, 15.0], 'Egypt': [26.0, 30.0], 'Ethiopia': [9.1, 40.5],
        'France': [46.0, 2.0], 'Germany': [51.0, 9.0], 'Ghana': [7.9, -1.0],
        'India': [20.0, 77.0], 'Indonesia': [-0.8, 113.9], 'Iran': [32.4, 53.7],
        'Iraq': [33.2, 43.7], 'Kazakhstan': [48.0, 66.9], 'Kenya': [-0.0, 37.9],
        'Libya': [26.3, 17.2], 'Madagascar': [-18.8, 47.0], 'Mali': [17.6, -3.0],
        'Mexico': [23.6, -102.5], 'Mongolia': [46.9, 103.8], 'Morocco': [31.8, -7.1],
        'Myanmar': [21.9, 95.9], 'Niger': [17.6, 8.1], 'Nigeria': [9.1, 8.7],
        'Pakistan': [30.4, 69.3], 'Peru': [-9.2, -75.0], 'Philippines': [12.9, 121.8],
        'Russia': [61.5, 105.3], 'Saudi Arabia': [23.9, 45.1], 'Somalia': [5.2, 46.2],
        'South Africa': [-30.6, 22.9], 'Sudan': [12.9, 30.2], 'Tanzania': [-6.4, 34.9],
        'Thailand': [15.9, 100.6], 'Turkey': [38.8, 35.2], 'Ukraine': [48.4, 31.2],
        'United Kingdom': [55.4, -3.4], 'United States': [37.1, -95.7],
        'Uzbekistan': [41.4, 64.6], 'Venezuela': [6.4, -66.6], 'Vietnam': [14.1, 108.3],
        'Yemen': [15.6, 48.0], 'Zambia': [-13.1, 27.8]
    }
    
    # Add coordinates
    df_combined_grouped['lat'] = df_combined_grouped['country'].map(
        lambda x: country_coords.get(x, [None, None])[0]
    )
    df_combined_grouped['lon'] = df_combined_grouped['country'].map(
        lambda x: country_coords.get(x, [None, None])[1]
    )
    
    # Filter countries with valid coordinates
    df_scatter_overlay = df_combined_grouped[
        (df_combined_grouped['lat'].notna()) & 
        (df_combined_grouped['lon'].notna()) &
        (df_combined_grouped['cases_per_million'] >= 0)
    ].copy()
    
    # Create figure
    fig_vaccination_map = go.Figure()
    
    # Add initial choropleth
    first_period = sorted(df_combined_grouped['period_label'].unique())[0]
    first_period_data = df_combined_grouped[df_combined_grouped['period_label'] == first_period]
    
    fig_vaccination_map.add_trace(
        go.Choropleth(
            locations=first_period_data['code'],
            z=first_period_data['pol3_immunization_rate'],
            text=first_period_data['vaccination_category'],
            customdata=first_period_data['country'],
            colorscale=[[0, '#D32F2F'], [0.25, '#FF7043'], [0.5, '#FDD835'], 
                       [0.75, '#66BB6A'], [1, '#2E7D32']],
            zmin=0,
            zmax=100,
            showscale=False,
            hovertemplate='<b>%{customdata}</b><br>' +
                          'Cobertura: %{z:.1f}%<br>' +
                          'Categoría: %{text}<br>' +
                          '<extra></extra>',
            name='Cobertura Vacunación',
            showlegend=False
        )
    )
    
    # Add initial scatter
    first_scatter_data = df_scatter_overlay[df_scatter_overlay['period_label'] == first_period]
    if len(first_scatter_data) > 0:
        fig_vaccination_map.add_trace(
            go.Scattergeo(
                lon=first_scatter_data['lon'],
                lat=first_scatter_data['lat'],
                mode='markers',
                marker=dict(
                    size=first_scatter_data['bubble_size'],
                    color='rgba(139, 0, 0, 0.8)',
                    line=dict(width=2, color='white'),
                    symbol='circle'
                ),
                hovertext=first_scatter_data['country'],
                customdata=first_scatter_data['cases_per_million'].round(2),
                hovertemplate='<b>%{hovertext}</b><br>' +
                              'Casos por millón: %{customdata}<br>' +
                              '<extra></extra>',
                name='Casos de Polio (por millón)',
                showlegend=False
            )
        )
    
    # Create animation frames
    frames = []
    for period in sorted(df_combined_grouped['period_label'].unique()):
        period_choropleth = df_combined_grouped[df_combined_grouped['period_label'] == period]
        period_scatter = df_scatter_overlay[df_scatter_overlay['period_label'] == period]
        
        frame_data = [
            go.Choropleth(
                locations=period_choropleth['code'],
                z=period_choropleth['pol3_immunization_rate'],
                text=period_choropleth['vaccination_category'],
                customdata=period_choropleth['country'],
                colorscale=[[0, '#D32F2F'], [0.25, '#FF7043'], [0.5, '#FDD835'], 
                           [0.75, '#66BB6A'], [1, '#2E7D32']],
                zmin=0,
                zmax=100,
                showscale=False,
                hovertemplate='<b>%{customdata}</b><br>' +
                              'Cobertura: %{z:.1f}%<br>' +
                              'Categoría: %{text}<br>' +
                              '<extra></extra>'
            )
        ]
        
        if len(period_scatter) > 0:
            frame_data.append(
                go.Scattergeo(
                    lon=period_scatter['lon'],
                    lat=period_scatter['lat'],
                    mode='markers',
                    marker=dict(
                        size=period_scatter['bubble_size'],
                        color='rgba(139, 0, 0, 0.8)',
                        line=dict(width=2, color='white'),
                        symbol='circle'
                    ),
                    hovertext=period_scatter['country'],
                    customdata=period_scatter['cases_per_million'].round(2),
                    hovertemplate='<b>%{hovertext}</b><br>' +
                                  'Casos por millón: %{customdata}<br>' +
                                  '<extra></extra>'
                )
            )
        
        frames.append(go.Frame(data=frame_data, name=period))
    
    fig_vaccination_map.frames = frames
    
    # Create custom legend annotations
    MAP_LEFT, MAP_RIGHT = 0.15, 0.85
    LEGEND_OFFSET = 0.02
    LX = MAP_LEFT - LEGEND_OFFSET
    RX = MAP_RIGHT + LEGEND_OFFSET
    YS_LEFT = 0.85
    YS_RIGHT = 0.85
    ROW = 0.035
    
    left_items = [
        '<span style="color:#2E7D32; font-size:18px">■</span> Muy Alta (≥95%)',
        '<span style="color:#66BB6A; font-size:18px">■</span> Alta (85-94%)',
        '<span style="color:#FDD835; font-size:18px">■</span> Media (70-84%)',
        '<span style="color:#FF7043; font-size:18px">■</span> Baja (50-69%)',
        '<span style="color:#D32F2F; font-size:18px">■</span> Muy Baja (&lt;50%)',
    ]
    
    right_items = [
        '<span style="color:rgba(139, 0, 0, 0.8); font-size:14px">●</span> Punto pequeño (Pocos casos)',
        '<span style="color:rgba(139, 0, 0, 0.8); font-size:20px">●</span> Punto mediano (Casos moderados)',
        '<span style="color:rgba(139, 0, 0, 0.8); font-size:28px">●</span> Punto grande (Muchos casos)',
    ]
    
    annotations = [
        # Headers
        dict(x=LX, y=YS_LEFT, xref='paper', yref='paper', xanchor='right',
             text='<b>Cobertura de vacunación</b>', showarrow=False,
             align='left', font=dict(size=12, color='black', family='Arial'),
             bgcolor='rgba(255,255,255,0.95)', borderwidth=0),
        dict(x=RX, y=YS_RIGHT, xref='paper', yref='paper', xanchor='left',
             text='<b>Casos por millón</b>', showarrow=False,
             align='right', font=dict(size=12, color='black', family='Arial'),
             bgcolor='rgba(255,255,255,0.95)', borderwidth=0),
    ]
    
    # Left legend items
    for i, txt in enumerate(left_items, start=1):
        annotations.append(dict(
            x=LX, y=YS_LEFT - i*ROW, xref='paper', yref='paper',
            xanchor='right', text=txt, showarrow=False,
            align='left', font=dict(size=10, color='black')
        ))
    
    # Right legend items
    for i, txt in enumerate(right_items, start=1):
        annotations.append(dict(
            x=RX, y=YS_RIGHT - i*ROW, xref='paper', yref='paper',
            xanchor='left', text=txt, showarrow=False,
            align='right', font=dict(size=10, color='black')
        ))
    
    # Update layout
    fig_vaccination_map.update_layout(
        width=1700,
        height=850,
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='natural earth',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            coastlinecolor='rgb(204, 204, 204)',
            domain=dict(x=[MAP_LEFT, MAP_RIGHT], y=[0.15, 0.9])
        ),
        title=dict(
            text='Cobertura de Vacunación Pol3 vs. Casos de Polio por Millón de Habitantes<br>'
                 '<span style="font-size:14px;">Color del mapa: % de vacunación | Tamaño de puntos: Casos por millón</span>',
            x=0.5, y=0.95, font=dict(size=18)
        ),
        margin=dict(l=120, r=120, t=120, b=120),
        annotations=annotations,
        # Animation controls
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=[
                    dict(
                        args=[None, {"frame": {"duration": 2000, "redraw": True},
                                    "fromcurrent": True,
                                    "transition": {"duration": 500, "easing": "cubic-in-out"},
                                    "mode": "immediate"}],
                        label="▶ Start",
                        method="animate"
                    ),
                    dict(
                        args=[[None], {"frame": {"duration": 0, "redraw": False},
                                      "mode": "immediate",
                                      "transition": {"duration": 0}}],
                        label="⏸ Stop",
                        method="animate"
                    )
                ],
                pad={"r": 10, "t": 10},
                showactive=False,
                x=0.01,
                xanchor="left",
                y=0.05,
                yanchor="bottom",
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="rgba(0,0,0,0.3)",
                borderwidth=1,
                font=dict(size=12)
            ),
        ],
        sliders=[dict(
            active=0,
            yanchor="top",
            xanchor="left",
            currentvalue=dict(
                font=dict(size=14, color="black"),
                prefix="Período: ",
                visible=True,
                xanchor="center"
            ),
            transition=dict(duration=300, easing="cubic-in-out"),
            pad=dict(b=10, t=40),
            len=0.8,
            x=0.1,
            y=0,
            steps=[
                dict(
                    args=[[period], {"frame": {"duration": 300, "redraw": True},
                                   "mode": "immediate",
                                   "transition": {"duration": 300, "easing": "cubic-in-out"}}],
                    label=period,
                    method="animate"
                ) for period in sorted(df_combined_grouped['period_label'].unique())
            ],
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="rgba(0,0,0,0.3)",
            borderwidth=1,
            tickcolor="rgba(0,0,0,0.3)"
        )]
    )
    
    return fig_vaccination_map

# Create the charts
stacked_area_chart = create_stacked_area_chart(df_income_time)
vaccination_map = create_vaccination_map(df_polio_vaccine)

# Define app layout
app.layout = html.Div([
    html.Div([
        html.H1("Análisis de Polio: Cobertura de Vacunación y Casos", 
                style={'textAlign': 'center', 'marginBottom': 30, 'color': '#2B6387'}),
        
        html.P([
            "Este dashboard nos presenta un análisis de los casos de polio y su cobertura a nivel global. ",
            "Nuestros datos abarcan el período 1980-2016 y en donde se muestra la evolución temporal de la enfermedad en diferentes países."
        ], style={'textAlign': 'center', 'marginBottom': 40, 'fontSize': 16, 'color': '#666'}),
        
        # Tab system for different charts
        dcc.Tabs(id="tabs", value='tab-1', children=[
            dcc.Tab(label='Evolución de Casos por Grupo de Ingresos', value='tab-1', style={'fontSize': 16}),
            dcc.Tab(label='Mapa Interactivo Global', value='tab-2', style={'fontSize': 16}),
        ], style={'marginBottom': 30}),
        
        html.Div(id='tabs-content')
        
    ], style={'maxWidth': '1800px', 'margin': '0 auto', 'padding': '20px'})
])

@callback(Output('tabs-content', 'children'),
          Input('tabs', 'value'))
def render_content(active_tab):
    if active_tab == 'tab-1':
        return html.Div([
            html.H2("Evolución Temporal por Grupo de Ingresos", 
                    style={'textAlign': 'center', 'marginBottom': 20, 'color': '#2B6387'}),
            
            html.P([
                "Este gráfico nos muestra la evolución de los casos de polio per cápita ",
                "para los distintos grupos de países según su nivel de ingresos. Podemos observar ",
                "un impacto desproporcionado en países de menores ingresos y la efectividad ",
                "de las campañas de vacunación globales a lo largo del tiempo."
            ], style={'textAlign': 'center', 'marginBottom': 30, 'fontSize': 14, 'color': '#666'}),
            
            html.Div([
                dcc.Graph(
                    figure=stacked_area_chart,
                    style={'height': '800px', 'width': '100%'},
                    config={'displayModeBar': True, 'responsive': True}
                )
            ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'}),
            
            html.Div([
                html.H3("Puntos Clave:", style={'color': '#2B6387', 'marginBottom': 10}),
                html.Ul([
                    html.Li("Los países de ingresos bajos y medio-bajos han sido los más afectados históricamente."),
                    html.Li("Se observa una reducción dramática en todos los grupos desde los años 1990s."),
                    html.Li("Los países de altos ingresos mantienen tasas muy bajas consistentemente."),
                    html.Li("La tendencia general muestra el éxito de las iniciativas globales de erradicación del polio.")
                ], style={'fontSize': 14, 'color': '#666'})
            ], style={'marginTop': 30, 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
        ])
    
    elif active_tab == 'tab-2':
        return html.Div([
            html.H2("Mapa Global Interactivo: Vacunación vs. Casos", 
                    style={'textAlign': 'center', 'marginBottom': 20, 'color': '#2B6387'}),
            
            html.P([
                "Este mapa animado combina dos visualizaciones: el color de cada país representa el nivel ",
                "de cobertura de vacunación, mientras que los círculos rojos indican la cantidad ",
                "de casos de polio por millón de habitantes."
            ], style={'textAlign': 'center', 'marginBottom': 30, 'fontSize': 14, 'color': '#666'}),
            
            html.Div([
                dcc.Graph(
                    figure=vaccination_map,
                    style={'height': '900px', 'width': '100%'},
                    config={'displayModeBar': True, 'responsive': True}
                )
            ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'}),
            
            html.Div([
                html.H3("Cómo Interpretar el Mapa:", style={'color': '#2B6387', 'marginBottom': 10}),
                html.Ul([
                    html.Li("🟩 Verde: Alta cobertura de vacunación (85%+)."),
                    html.Li("🟨 Amarillo: Cobertura media de vacunación (60-84%)."),
                    html.Li("🟥 Rojo: Baja cobertura de vacunación (<60%)."),
                    html.Li("⭕ Círculos rojos: Casos de polio por millón de habitantes.")
                ], style={'fontSize': 14, 'color': '#666'})
            ], style={'marginTop': 30, 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
        ])

# Run the app
if __name__ == '__main__':
    # Use PORT environment variable for deployment
    port = int(os.environ.get('PORT', 8050))
    app.run(debug=False, host='0.0.0.0', port=port)
