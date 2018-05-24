const path = require('path');
const webpack = require('webpack');

module.exports = {
  entry: './src/index.ts',
  plugins: [
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery'
    })
  ],
  module: {
    rules: [
      {
        test: /\.ts$/,
        loader: 'ts-loader',
        options: {
          configFile: path.resolve(__dirname, 'tsconfig.js')
        }
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      },
      {
        test: /\.(png|woff|woff2|eot|ttf|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/,
        loader: 'url-loader'
      }
    ]
  },
  resolve: {
    extensions: [ '.tsx', '.ts', '.js' ]
  },
  output: {
    filename: '[name]-bundle.js',
    path: path.resolve(__dirname, '../static/js'),
    library: 'rdrfts',
    libraryTarget: 'var'
  },
  optimization: {
    runtimeChunk: 'single',
    splitChunks: {
        chunks: 'all',
        cacheGroups: {
            default: {
                enforce: true,
                priority: 1
            },
            vendors: {
                test: /[\\/]node_modules[\\/]/,
                priority: 2,
                name: 'vendors',
                enforce: true,
                chunks: 'all'
            }
        }
    }
  }
};
