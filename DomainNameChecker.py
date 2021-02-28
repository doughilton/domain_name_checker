import json
import pandas as pd
import psycopg2
import requests

class DomainNameChecker:
    creds = json.loads(open("creds.json", "r").read())
    domainsdb_endpoint = "https://api.domainsdb.info/v1/domains/search?"

    # Get all domains containing "search_text" from API
    def get_domains(self, search_text):
        search_text = search_text.lower()
        domain_new = pd.Series(dtype = str)
        
        search_params = {"domain" : search_text,
                         "limit" : 100}
        
        r = requests.get(self.domainsdb_endpoint, params = search_params)
        r_response = r.json()
        
        domain_new = domain_new.append(pd.Series([domain_data["domain"].lower() for domain_data in r_response["domains"]]))
        next_page_id = r_response["next_page"]
        
        while next_page_id is not None:
            search_params["page"] = next_page_id
            r = requests.get(self.domainsdb_endpoint, params = search_params)
            r_response = r.json()
            domain_new = domain_new.append(pd.Series([domain_data["domain"].lower() for domain_data in r_response["domains"]]))
            next_page_id = r_response["next_page"]
            
        return domain_new
    
    # Update domains list in database for "search_text"
    def update_domain_list(self, domains_to_update, search_text):
        conn = psycopg2.connect(host="localhost",
                                database="domain_name_checker",
                                user=self.creds["user"],
                                password=self.creds["password"])
        
        cur = conn.cursor()
        
        command = "select domain_id, domain_name from domains where date_removed is null and search_term = '" + search_text + "'"
        cur.execute(command)
        domain_list = pd.DataFrame(cur.fetchall(), columns = ["domain_id", "domain_name"])
        conn.commit()
        conn.close()
        
        new_domains = domains_to_update[~domains_to_update.isin(domain_list["domain_name"])]
        
        if new_domains.empty:
            print("No Domains Added")
        else:
            print("New Domains Added:")
            print(new_domains.to_string(index=False))
            self.add_domains(new_domains, search_text)
            
        removed_domains = domain_list[~domain_list["domain_name"].isin(domains_to_update)]
        
        if removed_domains.empty:
            print("No Domains Removed")
        else:
            print("Domains Removed:")
            print(removed_domains["domain_name"].to_string(index=False))
            self.remove_domains(removed_domains["domain_id"].map(str))
            
        pass
    
    # Add new domain entry
    def add_domains(self, domains_to_add, search_text):
        conn = psycopg2.connect(host="localhost",
                            database="domain_name_checker",
                            user=self.creds["user"],
                            password=self.creds["password"])
        
        cur = conn.cursor()
        
        new_domains_str = ','.join(["('" + d_name + "', '" + search_text + "')" for d_name in domains_to_add])
        sql_insert = "INSERT INTO domains(domain_name, search_term) VALUES " + new_domains_str
        cur.execute(sql_insert)
        conn.commit()
        conn.close()
        
        pass
        
    # Mark domains removed
    def remove_domains(self, domains_to_remove):
        conn = psycopg2.connect(host="localhost",
                        database="domain_name_checker",
                        user=self.creds["user"],
                        password=self.creds["password"])
        
        cur = conn.cursor()
        removed_domains_str = ','.join(domains_to_remove)
        sql_update = "UPDATE domains SET date_removed = NOW() WHERE domain_id IN (" + removed_domains_str + ")"
        cur.execute(sql_update)
        conn.commit()
        conn.close()
        
        pass


# Code to run each night
search_text = "lava"
domainNameChecker = DomainNameChecker()
todays_domains = domainNameChecker.get_domains(search_text)
domainNameChecker.update_domain_list(todays_domains, search_text)