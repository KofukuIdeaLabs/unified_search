from io import StringIO
import pandas as pd
import numpy as np
import re
import os


class ExcelFileParser:

    def __init__(self):
        pass

    def find_table_beginnings(self,df, row_threshold, col_threshold, max_empty_rows, max_empty_cols):
        '''Identify row and column indices where tables begin based on changes in non-NaN cell counts'''
        n_values_row = np.logical_not(df.isnull()).sum(axis=1)
        n_values_col = np.logical_not(df.isnull()).sum(axis=0)
        
        row_diff = n_values_row.diff().fillna(0)
        col_diff = n_values_col.diff().fillna(0)
        
        row_indices = np.where(row_diff > row_threshold)[0]
        col_indices = np.where(col_diff > col_threshold)[0]
        
        table_beginnings = []
        for row_idx in row_indices:
            for col_idx in col_indices:
                if np.any(df.iloc[row_idx:, col_idx].notnull()):
                    end_col_adjusted = col_idx
                    empty_col_count = 0
                    
                    # Check for consecutive empty columns after col_idx
                    for j in range(col_idx -1,-1,-1):
                        if n_values_col[j] == 0:
                            empty_col_count += 1
                            if empty_col_count > max_empty_cols:
                                break
                        else:
                            empty_col_count = 0
                            end_col_adjusted = j  # Update end_col_adjusted for non-empty column

                    # Adjust start row for max empty rows within the table
                    start_row_adjusted = row_idx
                    empty_row_count = 0

                    # Check for consecutive empty rows before row_idx
                    for i in range(row_idx - 1, -1, -1):
                        if n_values_row[i] == 0:
                            empty_row_count += 1
                            if empty_row_count > max_empty_rows:
                                break
                        else:
                            empty_row_count = 0
                            start_row_adjusted = i  # Update start_row_adjusted for non-empty row
                    
                    table_beginnings.append((start_row_adjusted, end_col_adjusted))
        
        return table_beginnings


    def find_table_endings(self,df, row_threshold, col_threshold, max_empty_rows, max_empty_cols):
        '''Identify row and column indices where tables end based on changes in non-NaN cell counts and considering max empty rows and columns.'''
        n_values_row = np.logical_not(df.isnull()).sum(axis=1)
        n_values_col = np.logical_not(df.isnull()).sum(axis=0)

        
        row_diff = n_values_row.diff().fillna(0)
        col_diff = n_values_col.diff().fillna(0)

        print(row_diff)
        print(col_diff)
        
        # Initialize row_indices and col_indices to capture indices where the difference is significant
        row_indices = np.where(row_diff < -row_threshold)[0]
        col_indices = np.where(col_diff < -col_threshold)[0]
        
        table_endings = []
        
        for row_idx in row_indices:
            for col_idx in col_indices:
                if np.any(df.iloc[:row_idx, col_idx].notnull()):
                    # Adjust end row for max empty rows within the table
                    end_row_adjusted = row_idx
                    empty_row_count = 0
                    
                    # Check for consecutive empty rows after row_idx
                    for i in range(row_idx + 1, len(n_values_row)):
                        if n_values_row[i] == 0:
                            empty_row_count += 1
                            if empty_row_count > max_empty_rows:
                                break
                        else:
                            empty_row_count = 0
                            end_row_adjusted = i  # Update end_row_adjusted for non-empty row
                    
                    # Adjust end column for max empty columns within the table
                    end_col_adjusted = col_idx
                    empty_col_count = 0
                    
                    # Check for consecutive empty columns after col_idx
                    for j in range(col_idx + 1, len(n_values_col)):
                        if n_values_col[j] == 0:
                            empty_col_count += 1
                            if empty_col_count > max_empty_cols:
                                break
                        else:
                            empty_col_count = 0
                            end_col_adjusted = j  # Update end_col_adjusted for non-empty column
                    
                    table_endings.append((end_row_adjusted, end_col_adjusted))
        
        return table_endings
    
    def group_coordinates(self,beginnings, endings, df_shape):
        max_row, max_col = df_shape
        
        # If no beginnings and no endings are provided, return the entire sheet
        if not beginnings or not endings:
            return [((0, 0), (max_row - 1, max_col - 1))]
        
        # # If no beginnings are provided, use the largest possible ending from the start
        # if not beginnings:
        #     largest_ending = max(endings, key=lambda x: (x[0], x[1]))
        #     return [((0, 0), largest_ending)]
        
        # if not endings:
        #     endings = [(max_row - 1, max_col - 1)]
        
        beginnings = sorted(beginnings)
        endings = sorted(endings, key=lambda x: (x[0], x[1]))
        
        groups = []
        used_endings = set()
        
        for start_row, start_col in beginnings:
            selected_ending = None
            
            for end_row, end_col in endings:
                if end_row >= start_row and end_col >= start_col:
                    selected_ending = (end_row, end_col)
                    break
            
            if selected_ending:
                # Check for overlapping groups and adjust accordingly
                overlapping = False
                for group in groups:
                    if group[0] <= (start_row, start_col) <= group[1] or group[0] <= selected_ending <= group[1]:
                        overlapping = True
                        break
                
                if not overlapping:
                    groups.append(((start_row, start_col), selected_ending))
                    used_endings.add(selected_ending)
        
        return groups

    def parse_excel_sheet(self,file, sheet_name, row_threshold, col_threshold, max_empty_rows, max_empty_cols, is_csv=False):
        '''Parses multiple tables from an Excel sheet into multiple DataFrame objects. Returns [dfs, df_mds], where dfs is a list of dataframes and df_mds their potential associated metadata.'''
        # entire_sheet = pd.read_excel(file, sheet_name=sheet_name)

        if is_csv:
            entire_sheet = pd.read_csv(StringIO(file))
        else:
            file_extension = os.path.splitext(file)[1].lower()
            
            if file_extension in ['.xls', '.xlsx']:
                entire_sheet = pd.read_excel(file, sheet_name=sheet_name)
            else:
                raise ValueError("Unsupported file format")
        
        table_beginnings = list(set(self.find_table_beginnings(entire_sheet, row_threshold, col_threshold,max_empty_rows, max_empty_cols)))
        table_endings = list(set(self.find_table_endings(entire_sheet, row_threshold, col_threshold, max_empty_rows, max_empty_cols)))

        groups = self.group_coordinates(table_beginnings, table_endings, entire_sheet.shape)

        print(table_beginnings,"begin")
        print(table_endings,"ending")

        dfs = []
        df_mds = []
        
        for (start_row, start_col), (end_row, end_col) in groups:
            df = entire_sheet.iloc[start_row:end_row+1, start_col:end_col+1].dropna(how='all').dropna(axis=1, how='all')
            dfs.append(df)
            
            md = entire_sheet.iloc[:start_row].dropna(how='all').dropna(axis=1, how='all')
            df_mds.append(md)
        
        return dfs, df_mds
    
    def get_name(self,name):
        pattern = r'[_\s-]+'
        return re.sub(pattern, "_", name.lower())
    
    
    
    def execute(self, file_path, is_csv=False):
        '''Extracts tables for every sheet in the Excel file.'''
        result = {
            "dataframes": {},
        }
        if is_csv:
            """sheetnames will be page number from marker?, file_path is list of csv texts"""
            sheet_names = [f"table_{i}" for i in range(len(file_path))]
            file_path = dict(zip(sheet_names, file_path))
        else:
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names


        for sheet_name in sheet_names:
            if is_csv:
                dfs, df_mds = self.parse_excel_sheet(file_path[sheet_name], sheet_name,col_threshold=2,row_threshold=2,max_empty_rows=6,max_empty_cols=5, is_csv=is_csv)
            else:
                dfs, df_mds = self.parse_excel_sheet(file_path, sheet_name,col_threshold=2,row_threshold=2,max_empty_rows=6,max_empty_cols=5, is_csv=is_csv)
            df_dict = {}

            for i,df in enumerate(dfs):
                df_dict[f"table_{i}"] = df


            result["dataframes"][self.get_name(sheet_name)] = df_dict
        return result

        

excel_file_parser = ExcelFileParser()
