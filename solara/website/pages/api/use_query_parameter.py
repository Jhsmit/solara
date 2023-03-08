"""
# use_query_parameter

"""

import solara
from solara.website.utils import apidoc

title = "use_query_parameter"


# @solara.component
# def Page():
#     task, set_task = solara.use_query_parameter("task", "classification", str)
#     print(task)
#     solara.Select("Task:", value=task, on_value=set_task, values=["regression", "classification", "forecasting"])
#     if task == "regression":
#         solara.Button("Run Regression", icon_name="mdi-chart-line-variant")
#     elif task == "classification":
#         solara.Button("Run Classification", icon_name="mdi-chart-scatter-plot-hexbin")
#     else:
#         solara.Button("Run Forecasting", icon_name="mdi-chart-timeline")


@solara.component
def Page():
    count, set_count = solara.use_query_parameter("count", 2, int)
    if count > 0:
        solara.Text(f"👍" * count)
    if count == 0:
        solara.Text("🤔")
    else:
        solara.Text(f"👎" * (-count))
    solara.Button("Increment", on_click=lambda: set_count(count + 1))
    solara.Button("Decrement", on_click=lambda: set_count(count - 1))


__doc__ += apidoc(solara.use_query_parameter)  # type: ignore
