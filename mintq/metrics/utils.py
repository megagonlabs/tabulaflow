from mintq.schema import NL2QTaskOutput, PredQuery, GoldQuery


def get_final_gold_query(task: NL2QTaskOutput, check_exec_result: bool = True) -> GoldQuery:
    if task.task_type == "simple":
        res = task.gold_query
    elif task.task_type == "ambig":
        res = task.gold_intended_query  # type: ignore
    else:
        raise ValueError(f"Task type is not supported: {task.task_type}")

    if res is not None and check_exec_result and res.exec_result is None:
        raise ValueError("Gold query has no exec result")

    if res is None:
        raise ValueError("Gold query is None")

    return res


def get_final_pred_query(task: NL2QTaskOutput, check_exec_result: bool = True) -> PredQuery | None:
    if task.task_type == "simple":
        res = task.pred_query
    elif task.task_type == "ambig":
        res = task.pred_intended_query
    else:
        raise ValueError(f"Task type is not supported: {task.task_type}")

    if res is not None and check_exec_result and res.exec_result is None:
        raise ValueError("Pred query has no exec result")

    return res
