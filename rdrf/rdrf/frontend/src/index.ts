import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import * as search from './search';


declare global {
    interface Window {
      otu_search_config: search.SearchConfig
    }
};

// TODO revise if we should switch to multiple entry points instead.
// ie. one entrypoint for each page
export { init as init_tables } from './tables';
