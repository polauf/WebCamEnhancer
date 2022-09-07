import tkinter as tk
import tkinter.ttk as ttk
from typing import Union, Type, NewType

_tk_vars_type = NewType("TkVars" , Union[tk.StringVar, tk.BooleanVar, tk.IntVar, tk.DoubleVar])
_tk_vars_classes_type = NewType("TkVarTypes" ,Union[tuple([Type[t] for t in _tk_vars_type.__supertype__.__args__])])

def make_simple_setting_row(master: tk.Tk, i: int, text: str, default_value, var_class: _tk_vars_classes_type=tk.StringVar) -> _tk_vars_type:
    label = ttk.Label(master, text=text)
    label.grid(column=0, row=i, sticky="w")
    var = var_class(master)
    entry = tk.Entry(master, textvariable=var)
    entry.grid(column=1, padx=10, row=i, sticky="e")
    var.set(default_value)
    return var