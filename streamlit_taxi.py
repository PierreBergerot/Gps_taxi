import streamlit as st
import pandas as pd
import heapq
import plotly.express as px

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
    df = df[df['diff']>=pd.Timedelta(seconds=1)]
    df = df[df['diff']<=pd.Timedelta(minutes=5)]
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
    return df_connect

def create_adjency_list(df_adjency):
    df_adjency['point_a'] = df_adjency['longitude_a'].astype(str) + ' ' + df_adjency['latitude_a'].astype(str)
    df_adjency['point_b'] = df_adjency['longitude_b'].astype(str) + ' ' + df_adjency['latitude_b'].astype(str)
    df_adjency = df_adjency.drop(['longitude_a', 'latitude_a', 'longitude_b', 'latitude_b'], axis=1)

    adjacency_list = {}
    for index, row in df_adjency.iterrows():
        if row['point_a'] not in adjacency_list:
            adjacency_list[row['point_a']] = []
        adjacency_list[row['point_a']].append((row['point_b'], row['diff'].total_seconds()))

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
    return time, df_path

@st.cache
def plotly(df):
    df = df.sample(frac=0.25)
    fig = px.line_mapbox(df, lat="latitude", lon="longitude", zoom=12, height=1000)
    fig.update_layout(mapbox_style="stamen-terrain")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.update_traces(mode='markers')
    fig.update_layout(clickmode='event+select')
    return fig

@st.cache
def heatmap(df):
    df = df.sample(frac=0.50)
    fig = px.density_mapbox(df, lat='latitude', lon='longitude', z='diff', radius=10,zoom=12, mapbox_style="stamen-terrain")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

def slider_checkbox():
    option = st.sidebar.selectbox(
        'Choose between 2 option',
        ('densite', 'GPS'))
    return option

def main():
    df = read_clean_data()

    Option =slider_checkbox()
    if Option == 'densite':
        st.write("Densite")
        st.plotly_chart(heatmap(df))
    else:
        st.write("nous allons vous montrer le trajet le plus rapide entre deux points")
        fig = plotly(df)
        st.plotly_chart(fig)
    
        st.write("veuillez selectionner deux points")
        start_lat = st.text_input("start lat point")
        start_lon = st.text_input("start long point")
        start = start_lon + ' ' + start_lat
        start = str(start)
        end_lat = st.text_input("end lat point")
        end_lon = st.text_input("end long point")
        end = end_lon + ' ' + end_lat
        end = str(end)
        button = st.button("calculer le trajet le plus rapide")
        if button:
            print(df)
            df_connect = connect_two_point(df)
            time, df_path = all_thing(df_connect,start,end)
            st.write("le temps de trajet est de",time)
            st.map(df_path)
main()