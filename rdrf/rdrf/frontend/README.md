This is the proms frontend development folder.

RDRF does not use any files contain in this folder. This folder is only used for development in order to generate JS/CSS files 
(a React app) that are copied in the RDRF static folder.

This frontend folder is a create-react-app that build (with 'yarn build') these static JS/CSS files.
For the information this JS/CSS files are loaded into the proms base template (templates/proms/base.html).

The template has an object window.proms_config that is used by this React app. If you just need to tweak/fix the UI and 
you want to develop this app with 'yarn start' in isolation of RDRF (typical create-react-app dev url: http://localhost:3000), 
then you may want to manually edit the window.proms_config in the public/index.html file as it contains the question definitions.

Otherwise if you want to develop in RDRF (and test the full user journey), 
then use 'yarn build' to build the JS/CSS. They are automatically generated and copied in RDRF static folders.
You may need to force refresh the browser as the JS/CSS files do not contain hash number (something provided by create-react-app
but that we removed so it works the same as the webpack implementation - the reason been to not diverge too much from our 
current webpack implementation - it would not have been easy to dynamically load the create-react-app generated default JS/CSS file - .i.e. we would have need some regex code to load them - in counterpart we lose the benefit of the browser detecting a different file and so automatically reloading these files)

Note that in order to change the default JS/CSS file names and copy them in RDRF, we added a postbuild script called in package.json.