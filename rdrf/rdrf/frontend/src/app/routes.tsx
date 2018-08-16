import * as React from 'react';
import { Route, Switch } from 'react-router-dom';

import MapPage from '../pages/map_page';
import SearchPage from '../pages/search_page';
import ContextualPage from '../pages/contextual_page';

export default props => (
    <div>
        <Switch>
            <Route exact path="/" component={SearchPage} />
            <Route path="/map" component={MapPage} />
            <Route path="/contextual" component={ContextualPage} />
        </Switch>
    </div>
);

