import plotly.express as px


class TypesOfFormCompleted:
    def __init__(self, df, date_start, date_end):
        self.df = df
        self.start_date = df["COLLECTIONDATE"].min()
        self.end_date = df["COLLECTIONDATE"].max()


    @property
    def title(self):
        return f"{self.date_start} to {self.date_end}"

    @property
    def bar(self):
        return px.bar(
            self.df,
            x="form",
            y="count",
            title=self.title,
            width=400,
            height=400,
        )

    @property
    def pie(self):
        return px.pie(
            self.df,
            values="count",
            names="form",
            title=self.title,
            width=400,
            height=400,
        )
