# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == 'scorecards':
        from primus.cli.scorecard.scorecards import scorecards
        return scorecards
    elif name == 'scores':
        from primus.cli.score.scores import scores
        return scores
    elif name == 'score':
        from primus.cli.score.scores import score
        return score
    elif name == 'results':
        from primus.cli.result.results import results
        return results
    elif name == 'feedback':
        from primus.cli.feedback.commands import feedback
        return feedback
    elif name == 'tasks':
        from primus.cli.task.tasks import tasks
        return tasks
    elif name == 'task':
        from primus.cli.task.tasks import task
        return task
    elif name == 'items':
        from primus.cli.item.items import items
        return items
    elif name == 'item':
        from primus.cli.item.items import item
        return item
    elif name == 'iterative_config_fetching':
        from primus.cli.shared import iterative_config_fetching
        return iterative_config_fetching
    elif name == 'memoized_resolvers':
        from primus.cli.shared import memoized_resolvers
        return memoized_resolvers
    elif name == 'experiment':
        from primus.cli.experiment.experiments import experiment
        return experiment
    else:
        raise AttributeError(f"module 'primus.cli' has no attribute '{name}'")

__all__ = ['scorecards', 'scores', 'score', 'results', 'feedback', 'tasks', 'task', 'items', 'item', 'iterative_config_fetching', 'memoized_resolvers', 'experiment']
