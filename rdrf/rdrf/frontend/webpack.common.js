const path = require('path');
const webpack = require('webpack');

module.exports = {
  entry: './src/init.tsx',
  module: {
    rules: [
      {
        test: /\.(ts|tsx)$/,
        loader: 'ts-loader',
        options: {
          configFile: path.resolve(__dirname, 'tsconfig.json')
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
    path: path.resolve(__dirname, '../static/rdrf/js'),
    library: 'otu',
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
