import plotly.express as px


class TypesOfFormCompleted:
    def __init__(self, df, date_start, date_end):
        self.df = df
        self.date_start = date_start.date()
        self.date_end = date_end.date()

    @property
    def title(self):
        return f"{self.date_start} to {self.date_end}"

    @property
    def figure(self):
        return px.bar(
            self.df,
            x="form",
            y="percentage",
            range_y=[0, 100],
            title=self.title,
            width=400,
            height=400,
        )

    @property
    def pie(self):
        return px.pie(
            self.df,
            values="percentage",
            names="form",
            title=self.title,
            width=400,
            height=400,
        )
