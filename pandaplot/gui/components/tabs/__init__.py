# Tab classes are intentionally NOT re-exported here: ChartTab pulls in the
# matplotlib Qt backend and NoteTab pulls in markdown. Import them from their
# own modules at point of use so app startup stays fast.