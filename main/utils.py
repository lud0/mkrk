import pandas as pd


def resample_timeseries(data):
    """
    Function to resample timeseries data wich outputs 1 day data point using the average value of the day
    :param data: list of tuples (date, score)
    :return: list of tuples (date, score)
    """
    df = pd.DataFrame.from_records(data, columns=['date', 'score'])

    # convert date column in pandas datetime format
    df['date'] = pd.to_datetime(df['date'])

    # set it as index
    df = df.set_index('date')

    # resample using 1 day bins and taking the average value
    d2 = df.resample('D').mean()

    # set the nan to 0
    d2 = d2.fillna(0)

    # convert the dates into strings
    d2['date'] = d2.index.to_series()
    d2['date'] = pd.to_datetime(d2['date'])
    d2['date'] = d2['date'].dt.strftime('%Y-%m-%d')
    d2 = d2.set_index('date')

    # return the new data as list of tuples
    return list(d2.itertuples(name=None))
