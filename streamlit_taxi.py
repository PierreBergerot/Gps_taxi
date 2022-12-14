import streamlit as st
import pandas as pd
import heapq
import plotly.express as px
import datetime

@st.cache
def read_clean_data():
    colum_names=['taxi id', 'date time', 'longitude', 'latitude']

    taxi_id = [6275,3015,3557,3579,8179]
    df = pd.DataFrame(columns=colum_names)
    for i in range(len(taxi_id)):
        df_15 = pd.read_csv('taxi_log_2008_by_id/'+str(taxi_id[i])+'.txt', names=colum_names)
        df = pd.concat([df, df_15], axis=0)
    df = df.drop_duplicates()
    df['date time']=pd.to_datetime(df['date time'], format='%Y-%m-%d %H:%M:%S')
    df['longitude'] = df['longitude'].round(3)
    df['latitude'] = df['latitude'].round(3)
    df = df.sort_values(by=['taxi id','date time'])
    df = df.reset_index(drop=True)
    df = df[(df['longitude']>=116.215140) & (df['longitude']<=116.586700) & (df['latitude']>=39.757610) & (df['latitude']<=40.079850)]
    df = df.reset_index(drop=True)
    df['diff'] = df['date time'].diff()
    df = df[df['diff']>=pd.Timedelta(seconds=0)]
    df = df.reset_index(drop=True)
    return df

def connect_two_point(df):
    df_connect = df[['longitude', 'latitude']].copy()
    df_connect.columns = ['longitude_a', 'latitude_a']
    df_connect['longitude_b'] = df['longitude'].shift(-1)
    df_connect['latitude_b'] = df['latitude'].shift(-1)
    df_connect['diff'] = df['diff'].shift(-1)
    df_connect = df_connect.dropna()
    df_connect = df_connect.reset_index(drop=True)
    df_connect = df_connect.groupby(['longitude_a', 'latitude_a', 'longitude_b', 'latitude_b'])['diff'].mean().reset_index()

    df_connect['diff'] = df_connect['diff'].dt.total_seconds()
    
    df_connect['distance'] = ((df_connect['longitude_a']-df_connect['longitude_b'])**2 + (df_connect['latitude_a']-df_connect['latitude_b'])**2)**0.5
    df_connect = df_connect[df_connect['distance']<=0.01]
    df_connect = df_connect.drop(['distance'], axis=1)
    df_connect = df_connect.reset_index(drop=True)

    df_connect_2 = df_connect.copy()
    df_connect_2.columns = ['longitude_a', 'latitude_a', 'longitude_b', 'latitude_b', 'diff']
    df_connect_2['longitude_a'] = df_connect['longitude_b']
    df_connect_2['latitude_a'] = df_connect['latitude_b']
    df_connect_2['longitude_b'] = df_connect['longitude_a']
    df_connect_2['latitude_b'] = df_connect['latitude_a']
    df_connect_2['diff'] = df_connect['diff']
    df_connect = pd.concat([df_connect, df_connect_2], axis=0)
    df_connect = df_connect.drop_duplicates()
    df_connect = df_connect.reset_index(drop=True)

    return df_connect

def create_adjency_list(df_adjency):
    df_adjency['point_a'] = df_adjency['longitude_a'].astype(str) + ' ' + df_adjency['latitude_a'].astype(str)
    df_adjency['point_b'] = df_adjency['longitude_b'].astype(str) + ' ' + df_adjency['latitude_b'].astype(str)
    df_adjency = df_adjency.drop(['longitude_a', 'latitude_a', 'longitude_b', 'latitude_b'], axis=1)

    adjacency_list = {}
    for index, row in df_adjency.iterrows():
        if row['point_a'] not in adjacency_list:
            adjacency_list[row['point_a']] = []
        adjacency_list[row['point_a']].append((row['point_b'], row['diff']))

    return adjacency_list

def find_path(adjacency_list, start, end):
    def a_star(adjacency_list, start, goal):
        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {}
        cost_so_far = {}
        came_from[start] = None
        cost_so_far[start] = 0

        while frontier:
            current = heapq.heappop(frontier)[1]

            if current == goal:
                break

            for next in adjacency_list[current]:
                new_cost = cost_so_far[current] + next[1]
                if next[0] not in cost_so_far or new_cost < cost_so_far[next[0]]:
                    cost_so_far[next[0]] = new_cost
                    priority = new_cost
                    heapq.heappush(frontier, (priority, next[0]))
                    came_from[next[0]] = current

        return came_from, cost_so_far
    
    came_from, cost_so_far = a_star(adjacency_list, start, end)
    path = []
    current = end
    while current != None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path

def to_df(path):
    df = pd.DataFrame(path, columns=['point'])
    df['longitude'] = df['point'].apply(lambda x: x.split(' ')[0])
    df['latitude'] = df['point'].apply(lambda x: x.split(' ')[1])
    df = df.drop(['point'], axis=1)
    df['longitude'] = df['longitude'].astype(float)
    df['latitude'] = df['latitude'].astype(float)
    return df

def usable_data(df_path,df_connect):
    df_path['longitude_a'] = df_path['longitude'].shift(1)
    df_path['longitude_b'] = df_path['longitude']
    df_path['latitude_a'] = df_path['latitude'].shift(1)
    df_path['latitude_b'] = df_path['latitude']
    df_path = df_path.dropna()

    df_path = df_path.drop(['longitude', 'latitude'], axis=1)

    df_path['longitude_a'] = df_path['longitude_a'].astype(float)
    df_path['longitude_b'] = df_path['longitude_b'].astype(float)
    df_path['latitude_a'] = df_path['latitude_a'].astype(float)
    df_path['latitude_b'] = df_path['latitude_b'].astype(float)

    df_usable = pd.merge(df_path, df_connect, on=['longitude_a', 'latitude_a', 'longitude_b', 'latitude_b'], how='left')
    df_usable = df_usable.drop(['point_a','point_b'], axis=1)

    return df_usable

def all_thing(df_connect,start,end):
    adjacency_list = create_adjency_list(df_connect)
    path = find_path(adjacency_list, start, end)
    df_path = to_df(path)
    df_usable = usable_data(df_path,df_connect)
    time = df_usable['diff'].sum()
    time = datetime.timedelta(seconds=time)
    return time, df_path

@st.cache
def plotly(df):

    df = df.sample(frac=0.50)
    fig = px.line_mapbox(df, lat="latitude_a", lon="longitude_a", zoom=12, height=1000)
    fig.update_layout(mapbox_style="stamen-terrain")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.update_traces(mode='markers')
    fig.update_layout(clickmode='event+select')
    fig.update_layout(
        hovermode='closest',
        hoverlabel=dict(
            bgcolor="white",
            font_size=16,
            font_family="Rockwell"
        )
    )
    return fig

def count(df):
    df['count'] = df.groupby(['longitude', 'latitude'])['longitude'].transform('count')
    df = df.drop_duplicates(subset=['longitude', 'latitude'])
    df = df.reset_index(drop=True)
    return df

@st.cache
def heatmap(df):
    df = df.sample(frac=0.50)
    df = count(df)
    fig = px.density_mapbox(df, lat='latitude', lon='longitude', z='count', radius=10, zoom=12, mapbox_style="stamen-terrain")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

def slider_checkbox():
    option = st.sidebar.selectbox(
        'Choose between 2 option',
        ('density', 'GPS'))
    return option

def main():
    df = read_clean_data()

    Option =slider_checkbox()
    if Option == 'density':
        st.write("Density")
        st.plotly_chart(heatmap(df))
    else:
        st.write("We will show you the path between 2 points")
        df_connect = connect_two_point(df)
        fig = plotly(df_connect)
        st.plotly_chart(fig)
    
        st.sidebar.write("select the two points")
        start_lat = st.sidebar.text_input("start lat point")
        start_lon = st.sidebar.text_input("start long point")
        start = start_lon + ' ' + start_lat
        start = str(start)
        end_lat = st.sidebar.text_input("end lat point")
        end_lon = st.sidebar.text_input("end long point")
        end = end_lon + ' ' + end_lat
        end = str(end)
        button = st.sidebar.button("Find the path")
        if button:
            time, df_path = all_thing(df_connect,start,end)
            st.write("the time for the fare",time)
            st.map(df_path)
main()