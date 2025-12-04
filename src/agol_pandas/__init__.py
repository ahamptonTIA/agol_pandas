import os, uuid, re
import pandas as pd
import tempfile
from arcgis.gis import GIS
import time
#--------------------------------------------------------------------------------
def get_temp_file(suffix: str = ".csv"):
    """
    Returns a path to a temporary file in the default temp directory.

    Parameters
    ----------
    suffix : str 
    Returns:
    A path to a temporary file.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            return (f.name, True)
    except Exception as e:
        return (str(e), False)
#--------------------------------------------------------------------------------
def convert_dts_utc(df: pd.DataFrame):
    """
    Converts all datetime columns in a Pandas dataframe to UTC timezone.

    Parameters
    ----------
    df : pd.DataFrame
        The Pandas dataframe to convert.

    Returns
    -------
    df : pd.DataFrame
        The Pandas dataframe with all datetime columns converted to 
        UTC timezone.
    """   
    try:
        cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

        for col in cols:

            if df[col].dtype == 'datetime64[ns]':

                df[col] = pd.to_datetime(df[col]).dt.tz_localize('UTC')

            else:

                df[col] = pd.to_datetime(df[col])
                df[col] = df[col].dt.tz_convert('UTC')

        return(df, True)    
    except Exception as e:
        return (str(e), False)
#--------------------------------------------------------------------------------
def normalize_service_name(service_name: str):
    """
    Normalizes a service name to follow the ArcGIS naming 
    convention rules.
    Service names must be a validated, which means it must only contain 
    letters, numbers, and/or underscores while being no longer than 128 
    characters.
    
    Parameters
    ----------
    service_name : str
        The name of the service to normalize.
        
    Returns
    -------
    str
        The normalized service name.
    """
    try:
        # Remove all leading and trailing whitespace.
        service_name = service_name.strip()
        # ensure the name does not start with a number
        if service_name[0].isdigit():
            service_name = f'_{service_name}'
        # Replace all characters that are not letters, numbers, or underscores.
        service_name = re.sub(r"[^\w]", "_", service_name)
        # Replace all consecutive underscore characters wit a single underscore.
        service_name = re.sub('_+', '_', service_name)
        # Convert the name to lowercase.
        service_name = service_name.lower()
        # Truncate the name to 128 characters.
        if len(service_name) > 128:
            service_name = service_name[:128]
        return (service_name, True)
    except Exception as e:
        return (str(e), False)        
#--------------------------------------------------------------------------------
def df_to_pandas_chunks(df, chunk_size=100000, keys=[]):
    """
    Generator that sorts and then chunks a PySpark 
    or pandas DataFrame into DataFrames of the given
    chunk size.
    
    Parameters
    ----------
    df : pd.DataFrame or pyspark.sql.DataFrame
        The dataframe to sort and chunk.
    chunk_size: int
        The max size of each chunk
    keys: str or list
        Column name or list of column names to sort 
        a dataframe on before chunking.
        Default, None - Sorting will not be applied
        
    Returns
    -------
    generator : A generator that yields chunks of pandas DataFrames.
    """    
    try:
        # if a key was supplied, sort the dataframe
        if bool(keys):
            if not isinstance(keys, list):
                keys = [keys]
                
        # sort and yield chunked pandas dataframes from pyspark
        if not isinstance(df, pd.DataFrame):
            df = df.orderBy(keys)
            for i in range(0, df.count(), chunk_size):
                chunk = df.toPandas()[i:i + chunk_size]
                yield chunk
        else:
            # sort and yield chunked pandas dataframes
            if bool(keys):
                df = df.sort_values(by=keys)
            for i in range(0, len(df), chunk_size):
                chunk = df[i:i + chunk_size]
                yield chunk
    except Exception as e:
        raise Exception(f"Failed to chunk DataFrame: {str(e)}")
#---------------------------------------------------------------------------------- 
def agol_hosted_item_to_sdf(gis: GIS, item_id: str):
    """
    Reads all data from a hosted layer or tableon ArcGIS Online 
    into a Pandas dataframe.
    
    Parameters
    ----------
    gis : GIS
        The ArcGIS object to use for connecting to ArcGIS Online.
    item_id : str
        The ID of the hosted layer or table on ArcGIS Online.
        
    Returns
    -------
    sdf : pd.DataFrame
        A Pandas dataframe containing the data from the hosted layer.
    """
    try:
        # Get the layer object from ArcGIS Online.
        item = gis.content.get(item_id)
        table = None
        
        # determine if the item has layers/tables
        if bool(item.layers):
            table = item.layers[0]    
        if bool(item.tables):
            table = item.tables[0]
            
        if not table:
            raise ValueError(f"Item {item_id} has no layers or tables.")

        # Get the query results from the layer.
        query_results = table.query(return_all_records=True)

        # Return the query results as a Pandas dataframe.
        return (query_results.sdf, True)
    except Exception as e:
        return (str(e), False) 
#-------------------------------------------------------------------------------- 
def set_unique_key_constraint(gis: GIS, table_id, key_field_name):
    """
    Function adds a unique key constraint to the specified hosted table or layer.
    
    Parameters:
        gis: GIS
            The ArcGIS object to use for connecting to ArcGIS Online.
        table_id: str: 
            The ID of the table.
        key_field_name str: 
            The name of the field to add the unique constraint to.
            
    Returns:
        bool: 
            True if the constraint was created successfully, False otherwise.
            
    **Example:**
    
    >>> # gis_object is an instance of arcgis.gis.GIS
    >>> set_unique_key_constraint(gis_object, 'my_table_id', 'my_field_name')
    True
    
    **Notes:**
    
    * The function checks if the field already has a unique index before creating a new one.
    * The function waits for the index to be created before returning.
    """
    try:
        item = gis.content.get(table_id) 
        tgt_table = None
        
        # determine if the item has layers/tables
        if bool(item.layers):
            tgt_table = item.layers[0] 
        if bool(item.tables):
            tgt_table = item.tables[0]
            
        if not tgt_table:
            raise ValueError(f"Item {table_id} has no layers or tables.")
        
        def fld_has_unique_idx(key_field_name):
            if not hasattr(tgt_table.properties, 'indexes'):
                return False
            idx_fld_names = [f.fields.lower() 
                            for f in tgt_table.properties.indexes 
                            if f.isUnique]
            return key_field_name.lower() in idx_fld_names
        
        
        if not fld_has_unique_idx(key_field_name):
            idxName = f'UX_{item.title.upper()}_{tgt_table._lazy_properties.name.upper()}_{key_field_name}_ASC'
            print(f'Adding index to {tgt_table._lazy_properties.name} on field "{key_field_name}" named as "{idxName}"')
            new_idx = {}
            new_idx['name'] = idxName
            new_idx['fields'] = key_field_name
            new_idx['isUnique'] = True
            new_idx['description'] = "Field properties"
            tgt_table.manager.add_to_definition({"indexes":[new_idx]})

            status = False
            for x in range(12): # attempt every 5 secs for 1 min
                time.sleep(5)
                status = fld_has_unique_idx(key_field_name)
                if status:
                    print('\t-Index created successfully!')
                    break
            return (status, True)
        else:
            return (True, True)
    except Exception as e:
        return (str(e), False)
#--------------------------------------------------------------------------------
def df_to_agol_hosted_table(gis, df, item_id, mode='append', 
                            upsert_column=None, chunk_size=100000,
                            item_properties={}):
    """
    Function will "append", "overwrite", "upsert", 
    "update", or "insert" data from a pandas dataframe
    into an existing hosted ArcGIS Online table.
    
    Parameters
    ----------
    gis : ArcGIS python api portal GIS object, required
        ArcGIS python api portal GIS object
    df : Pandas dataframe or object, required 
    item_id : str, required
        AGOL resource/item ID for a table   
    mode : str, optional
        Data append method, options include "append", "overwrite",
        "upsert", "update", and "insert"  
    upsert_column : str, *optional
        Name of the unique key column required to use "upsert", 
        "update", or "insert" modes      
    chunk_size : int, optional
        The number of rows to include in each chunk.
        If not specified, a default chunk size will be used.
        
    Returns
    -------
    result : list
        List containing a dictionary detailing the results of each 
        attempt to push data into the target table to include the
        chunk id, chunk size, mode, and the Boolean result where
        True = success.
        
    Example:
        [
          {
            'chunk_id': 1, 
            'chunk_size': 500,
            'mode' : 'append', 
            'result': True
          }
        ]                              
    """        
    results = []
    tmp_csv = None
    tmp_table = None
    
    try:
        # check the supplied mode
        modes = ["append", "overwrite", "upsert", "update", "insert"]
        if mode not in modes:
            raise ValueError(f'Unidentified mode supplied: "{mode}"')
    
        # Check if the dataframe is empty
        if len(df) == 0:
            raise ValueError("The dataframe is empty.")
    
        # attempt to convert datetime stamps to UTC TZ for AGOL
        try:
            df, pStatus = convert_dts_utc(df)
            if not pStatus: 
                print('Failed to convert datetime stamps')
        except:
            pass
    
        # get the target item table
        item = gis.content.get(item_id) 

        tgt_table = None
        if item:
            # determine if the item has layers/tables
            if bool(item.layers):
                tgt_table = item.layers[0]
            if bool(item.tables):
                tgt_table = item.tables[0]
        else:
            print(f'Item with ID {item_id} not found')
            return (f'Item with ID {item_id} not found', False)
            
        # set the append params
        upsert=False
        skip_inserts=False
        skip_updates=False
        upsert_matching_field=None
    
        if mode == 'overwrite':
            if tgt_table:
                tgt_table.manager.truncate()
            else:
                raise ValueError("Cannot truncate: Target table not found.")
    
        elif mode in ['upsert', 'update', 'insert']:
            if not upsert_column:
                raise ValueError("""Upsert, update, and insert, require a column with unique keys must be identified.\n
                                See: https://doc.arcgis.com/en/arcgis-online/manage-data/add-unique-constraint.htm""")
            if mode =='update':
                skip_inserts=True
            if mode =='insert':
                skip_updates=True        
            upsert=True
            upsert_matching_field=upsert_column
    
        # Split the dataframe into chunks
        if len(df) > chunk_size:
            chunks = list(df_to_pandas_chunks(df, chunk_size=chunk_size, keys=[]))
        else:
            chunks = [df]
    
        if not chunks or (len(chunks) == 1 and len(chunks[0]) == 0):
            raise ValueError("The dataframe could not be chunked, see chunk_size")
    
        # iterate the chunks and apply the data from the dataframe
        for idx, chunk in enumerate(chunks):
        
            # create a temp csv file path
            tmp_csv, pStatus = get_temp_file()
            if not pStatus:
                raise Exception(tmp_csv)
                
            chunk.to_csv(tmp_csv, index=False)
            # set the item properties dataframe
            if not bool(item_properties):
                item_properties = {"title" : tmp_csv}
            # add/upload the csv to the user's content
            tmp_table = gis.content.add(data=tmp_csv , 
                                         item_properties=item_properties)
            # get info about the file including fields types and sample records
            src_info = gis.content.analyze(item=tmp_table.id, 
                                           file_type='csv', 
                                           location_type='none')
    
            result = tgt_table.append(  item_id=tmp_table.id,
                                        upload_format="csv",
                                        source_info=src_info['publishParameters'],
                                        upsert=upsert,
                                        skip_updates=skip_updates,
                                        use_globalids=False,
                                        update_geometry=False,
                                        append_fields= df.columns.to_list(),
                                        rollback=True,
                                        skip_inserts=skip_inserts,
                                        upsert_matching_field=upsert_matching_field)
            tmp_table.delete()
            results.append({'chunk_id': (idx+1), 
                            'chunk_size': len(chunk),
                            'mode' : mode,
                            'result': result})
        return (results, True)
    except Exception as e:
        return (str(e), False) 
    finally:
        try:
            if tmp_csv and os.path.exists(tmp_csv):
                os.remove(tmp_csv)
        except:
            pass                
        try: 
            if bool(tmp_table):
                tmp_table.delete()
        except:
            pass
#-------------------------------------------------------------------------------
def create_table(gis, name, df, key_field_name, item_properties={}):
    """Internal function to upload a new
    csv and create a new hoasted table
    
    Parameters
    ----------   
    gis : arcgis.gis.GIS
        The GIS object to use for creating the feature service.
    name : str
        The name to use for the new feature service.
    df : pandas.DataFrame 
        The DataFrame containing the data to use for creating 
        the feature service.
    key_field_name : str
        The field name to set the unique key constraint on.
        
    Returns
    -------
    pub_table : AGOL table item
        Published AGOL table item
    """
    try:
        tmp_csv = None
        tmp_table = None
        # create a temp csv file path
        tmp_csv, pStatus = get_temp_file()
        if not pStatus:
            raise Exception(tmp_csv) 
        
        
        # export he dataframe to csv
        df.to_csv(tmp_csv, index=False)
        # set the item properties dataframe
        if 'title' not in item_properties:
            item_properties["title"] = name
        # add/upload the csv to the user's content
        tmp_table = gis.content.add(data=tmp_csv, 
                                    item_properties=item_properties,
                                    owner=gis.users.me.username)
        # publish the csv as a hoasted table
        pub_table = tmp_table.publish(None)
        # remove the temp csv file
        os.remove(tmp_csv)
        #---------------------------
        idx_test, _ = set_unique_key_constraint(gis, pub_table.id, key_field_name) 
        if not idx_test:
            raise ValueError("Could not create unique field constraint for appends!")
        #---------------------------        
        return (pub_table, True)
    except Exception as e:
        return (str(e), False) 
    finally:
        try: 
            if tmp_table:
                tmp_table.delete()
        except:
            pass
        try:
            if tmp_csv and os.path.exists(tmp_csv):
                os.remove(tmp_csv)
        except:
            pass 
#-------------------------------------------------------------------------------      
def create_hosted_table_from_dataframe(gis: GIS, name: str, df: pd.DataFrame, 
                                      chunk_size: int = 200000):
    """
    Function creates a new feature service from data in a Pandas or 
    ArcGIS Spatial DataFrame.
    
    Parameters
    ----------
    gis : arcgis.gis.GIS
        The GIS object to use for creating the feature service.
    name : str
        The name to use for the new feature service.
    df : pandas.DataFrame 
        The DataFrame containing the data to use for creating the feature service.
    chunk_size : int, optional
        The number of rows to include in each chunk.
        If not specified, a default chunk size will be used.
        
    Returns
    -------
    arcgis.gis.Item
        arcgis.gis table layer item/object
    """
    try:
        # Check if the dataframe is empty
        if len(df) == 0:
            raise ValueError("The dataframe is empty.")
    
        # format the service name
        tbl_name, pStatus = normalize_service_name(name)
        if not pStatus:
                print('Failed to normalize service name')
                
        # Check if the name is already in use
        name_avail = gis.content.is_service_name_available(tbl_name, "featureService")
        if not name_avail:
            qs = f'title:{name} AND owner:{gis.users.me.username} AND type:Feature Service'
            qr_results = gis.content.search(qs)
            if qr_results:
                qr = qr_results[0]
                qr_link = f'{gis.url}/home/item.html?id={qr.itemid}'
                print(f'Error service name:({tbl_name}) already exists! SEE: {qr_link}')
                return (qr, True)
            
        # attempt to convert datetime stamps to UTC TZ for AGOL
        try:
            df, pStatus = convert_dts_utc(df)
            if not pStatus: 
                print('Failed to convert datetime stamps')
        except:
            pass
    
        # Split the dataframe into chunks
        if len(df) > chunk_size:
            chunks = list(df_to_pandas_chunks(df, chunk_size=chunk_size, keys=[]))
        else:
            chunks = [df]
            
        if not chunks or (len(chunks) == 1 and len(chunks[0]) == 0):
            raise ValueError("The dataframe could not be chunked, see chunk_size")
    
        # find or initialize table variables
        items = gis.content.search(query=f"title:{tbl_name} AND type:Feature Service AND owner:{gis.users.me.username}")
        items = [i for i in items if i.title==tbl_name]
        table_id = None
        pub_table = None
        
        if len(items) > 0 :
            table_id = items[0].id
            pub_table = items[0]
            
        PLACEHOLDER_KEY_FIELD = df.columns[0] if len(df.columns) > 0 else 'ID'
            
        for idx, chunk in enumerate(chunks):
            if idx == 0 and not bool(table_id):
                pub_table, pStatus = create_table(gis, name=tbl_name, df=chunk, key_field_name=PLACEHOLDER_KEY_FIELD)
                if not pStatus:
                    raise ValueError(f"Table could not be published: {pub_table}")
                table_id = pub_table.id
            elif bool(table_id):
                df_to_agol_hosted_table(gis, 
                                        chunk, 
                                        table_id,
                                        mode='append',
                                        chunk_size=chunk_size)
        return (pub_table, True)             
    except Exception as e:
        return (str(e), False) 
#-------------------------------------------------------------------------------            
def create_or_update_item_from_df(gis, df, name=None, table_id=None, 
                                  key_field_name=None, chunk_size=200000):
    """
    Function creates a new feature service from data in a Pandas or 
    ArcGIS Spatial DataFrame.
    
    Parameters
    ----------
    gis : arcgis.gis.GIS
        The GIS object to use for creating the feature service.
    name : str
        The name to use for the new feature service.
    df : pandas.DataFrame 
        The DataFrame containing the data to use for creating the feature service.
    table_id : str, optional
        The ID of an existing AGOL table to update/upsert.
    key_field_name : str, required for creation or upsert
        The unique key column name required for creation and "upsert" mode.
    chunk_size : int, optional
        The number of rows to include in each chunk.
        If not specified, a default chunk size will be used.
        
    Returns
    -------
    arcgis.gis.Item
        arcgis.gis table layer item/object
    """
    status = []
    d = {}
    r = ''
    pub_table = None
    try:

        if not bool(name) and not bool(table_id):
            raise ValueError("An item ID or name is required.")
        
        # Check if the dataframe is empty
        if len(df) == 0:
            raise ValueError("The dataframe is empty.")
            
        if not bool(table_id) and not bool(key_field_name):
             raise ValueError("A unique 'key_field_name' is required to create a new table.")
    
        # format the service name
        tbl_name, pStatus = normalize_service_name(name)
        if not pStatus: 
                print('Failed to normalize service name')
        # attempt to convert datetime stamps to UTC TZ for AGOL
        try:
            df, pStatus = convert_dts_utc(df)
            if not pStatus: 
                print('Failed to convert datetime stamps')
        except:
            pass
    
        # Split the dataframe into chunks
        if len(df) > chunk_size:
            chunks = list(df_to_pandas_chunks(df, chunk_size=chunk_size, keys=[key_field_name]))
        else:
            chunks = [df]
            
        if not chunks or (len(chunks) == 1 and len(chunks[0]) == 0):
            raise ValueError("The dataframe could not be chunked, see chunk_size")
    
        for chunk in chunks:
            d = {'chunk': 'chunk', 'row_start': chunk.index[0] + 1, 
                    'row_end': chunk.index[-1] + 1, 'status': 'Error'}
            
            try:
                if not table_id:
                    # Search for existing item to use for updates
                    query=f"title:{name} AND type:Feature Service AND owner:{gis.users.me.username}"
                    items = gis.content.search(query=query)
                    items = [i for i in items if i.title==name]
                    if len(items) > 0 :
                        table_id = items[0].id
                        pub_table = gis.content.get(table_id) 
                    else:
                        # Create the new table
                        pub_table, pStatus = create_table(gis, 
                                                            name=name,
                                                            df=chunk,
                                                            key_field_name=key_field_name,
                                                            item_properties={})
                        if not pStatus:
                            d['status'] = 'Error'
                            status.append(d)  
                            raise ValueError(f"Table could not be published: {pub_table}")
                        else:
                            table_id = pub_table.id
                            print(f'Crated table "{name}" with ID: {table_id}')
                            d['status'] = 'Success'
                            status.append(d)   
                else:
                    # Update/Upsert the existing table
                    r, _ = df_to_agol_hosted_table(gis, chunk, table_id, mode='upsert',
                                        upsert_column=key_field_name, chunk_size=chunk_size)
                    d['status'] = 'Success'
                    d['Messages'] = str(r)
                    status.append(d)            
            except Exception as e:
                d['status'] = 'Error'
                d['Messages'] = str(f'{r} :  {e}')
                status.append(d)
                print(f'Failed to load chunk, Rows {chunk.index[0] + 1}-{chunk.index[-1] + 1}, {e}' )
        return(status, True)
    except Exception as e:
        d['status'] = 'Error'
        d['Messages'] = str(f'{r} :  {e}')
        status.append(d)  
        return (status, False)
