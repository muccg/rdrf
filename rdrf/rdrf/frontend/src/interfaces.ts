import { SearchConfig } from './search';

declare global {
  interface Window {
    otu_search_config: SearchConfig,
  }
}

