__author__ = 'aleaf'

import sys
import os
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import ImageGrid
import matplotlib.patheffects as PathEffects
import seaborn as sb
import textwrap
import calendar
import climate_stats as cs
import GSFLOW_utils as GSFu


#--modify the base rcParams for a few items
newparams = {'font.family': 'Univers 47 Condensed Light',
             'legend.fontsize': 10,
             'axes.labelsize': 10,
             'xtick.labelsize': 10,
             'ytick.labelsize': 10,
             'pdf.fonttype': 42,
             'pdf.compression': 0,
             'axes.formatter.limits': [-7, 9]}

# Update the global rcParams dictionary with the new parameter choices
plt.rcParams.update(newparams)

# set/modify global Seaborn defaults
# update any overlapping parameters in the seaborn 'paper' style with the custom values above
sb.set_context("paper", newparams)




class ReportFigures():

    def __init__(self, mode, compare_periods, baseline_period, gcms, spinup,
                 aggregated_results_folder, output_folder,
                 var_name_file,
                 timeseries_properties,
                 variables_table=pd.DataFrame(),
                 synthetic_timepers=None,
                 exclude=None,
                 default_font='Univers 47 Condensed Light',
                 title_font='Univers 67 Condensed',
                 box_colors = ['SteelBlue', 'Khaki']):

        plots_folder = os.path.join(output_folder, mode)
        if not os.path.isdir(plots_folder):
            os.makedirs(plots_folder)

        print "\ngetting info on {} variables...".format(mode)
        varlist = GSFu.getvars(aggregated_results_folder, mode)
        varlist = [v for v in varlist if v not in exclude]

        self.mode = mode
        self.varlist = varlist
        self.gcms = gcms
        self.spinup = spinup
        self.var_info = GSFu.get_var_info(var_name_file)
        self.aggregated_results_folder = aggregated_results_folder
        self.output_base_folder = output_folder
        self.output_folder = os.path.join(output_folder, mode)
        self.mode = mode
        self.compare_periods = compare_periods
        self.baseline_period = baseline_period
        self.synthetic_timepers = synthetic_timepers
        self.timeseries_properties = timeseries_properties
        self.default_font = default_font # for setting seaborn styles for each plot
        self.title_font = title_font # font for plot titles
        self.variables_table = variables_table
        self.dates = ['-'.join(map(str, per)) for per in compare_periods]
        self.box_colors = box_colors


        if not self.variables_table.empty:

            # if a variables table (DataFrame) was given, convert any empty fields to strings
            self.variables_table = self.variables_table.fillna(value='')



    def name_output(self, var, stat, type, quantile=None):
        # scheme to organize plot names and folders
        if quantile:
            stat = 'Q{:.0f}0'.format(10*(1-quantile))

        output_folder = os.path.join(self.output_folder, stat, type)
        os.makedirs(output_folder) if not os.path.isdir(output_folder) else None

        outfile = os.path.join(output_folder, '{}_{}_{}.pdf'.format(var, stat, type))
        return outfile


    def plot_info(self, var, stat, plottype, quantile=None):
        # Set plot titles and ylabels

        # set on the fly by reading the PRMS/GSFLOW variables file
        if self.variables_table.empty or self.mode != 'statvar' or self.mode != 'csv':
            title, xlabel, ylabel, calc = GSFu.set_plot_titles(var, self.mode, stat, self.var_info,
                                                         self.aggregated_results_folder,
                                                         plottype='box', quantile=quantile)
        # set using DataFrame from pre-made table
        else:
            info = self.variables_table[(self.variables_table['variable'] == var)
                                        & (self.variables_table['stat'] == stat)
                                        & (self.variables_table['plot_type'] == plottype)]

            title, xlabel = info.iloc[0]['title'], info.iloc[0]['xlabel']
            ylabel = '{}, {}'.format(info.iloc[0]['ylabel_0'], info.iloc[0]['ylabel_1'])
            calc = info.iloc[0]['calc']
        return title, xlabel, ylabel, calc


    def make_box(self, csvs, var, stat, quantile=None):

        title, xlabel, ylabel, calc = self.plot_info(var, stat, 'box', quantile=quantile)

        # calculate montly means for box plot
        boxcolumns, baseline = cs.period_stats(csvs, self.compare_periods, stat, self.baseline_period,
                                               calc=calc, quantile=quantile)

        # make box plot
        if 'month' in stat:
            fig, ax = sb_box_monthly(boxcolumns, baseline, self.compare_periods, ylabel, title=title,
                                     default_font=self.default_font, color=self.box_colors)
        else:
            fig, ax = sb_box_annual(boxcolumns, baseline, self.compare_periods, ylabel, title=title,
                                    default_font=self.default_font, color=self.box_colors)

        outfile = self.name_output(var, stat, 'box', quantile)
        fig.savefig(outfile, dpi=300)
        plt.close()


    def make_timeseries(self, csvs, var, stat, quantile=None):

        # Set plot titles and ylabels
        title, xlabel, ylabel, calc = self.plot_info(var, stat, 'timeseries', quantile=quantile)

        # calculate annual means
        dfs = cs.annual_timeseries(csvs, self.gcms, self.spinup, stat, calc=calc, quantile=quantile)

        # make 'fill_between' timeseries plot with  mean and min/max for each year
        fig, ax = timeseries(dfs, ylabel, self.timeseries_properties, self.synthetic_timepers/365.0, title=title,
                             default_font=self.default_font)

        outfile = self.name_output(var, stat, 'timeseries', quantile)
        fig.savefig(outfile, dpi=300)
        plt.close()


    def make_violin(self, csvs, var, stat, quantile=None):
        # Set plot titles and ylabels
        title, xlabel, ylabel, calc = self.plot_info(var, stat, 'box', quantile=quantile)

        # calcualte period statistics for violins
        boxcolumns, baseline = cs.period_stats(csvs, self.compare_periods, stat, self.baseline_period,
                                               calc=calc, quantile=quantile)

        # make violin plot
        fig, ax = sb_violin_annual(boxcolumns, baseline, self.compare_periods, ylabel, title=title,
                                   default_font=self.default_font, color=self.box_colors)

        outfile = self.name_output(var, stat, 'violin', quantile)
        fig.savefig(outfile, dpi=300)
        plt.close()


    def make_violin_legend(self):

        fig = plt.figure()
        ax = fig.add_subplot(111)
        handles=[]
        labels=[]
        for d in range(len(self.dates)):
            handles.append(plt.Rectangle((0, 0), 1, 1, fc=self.box_colors[d]))
            labels.append(self.dates[d])
        handles.append(plt.Line2D(range(10), range(10), color='r', linewidth=2))
        labels.append('Baseline conditions ({}-{})'.format(self.baseline_period[0], self.baseline_period[1]))
        handles.append(plt.Line2D(range(10), range(10), color='k', linewidth=1, linestyle=':'))
        labels.append('Upper/lower quartiles')
        handles.append(plt.Line2D(range(10), range(10), color='k', linewidth=1, linestyle='--'))
        labels.append('Median')
        handles.append(plt.scatter(1, 1, c='k', s=12, marker='o'))
        labels.append('Values')

        figlegend = plt.figure(figsize=(3, 2))
        figlegend.legend(handles, labels, title='Explanation', loc='center')

        outfile = os.path.join(self.output_base_folder, 'violin_legend.pdf')
        figlegend.savefig(outfile, dpi=300)
        plt.close('all')


    def make_box_legend(self):

        fig = plt.figure()
        handles=[]
        labels=[]
        for d in range(len(self.dates)):
            handles.append(plt.Rectangle((0, 0), 1, 1, fc=self.box_colors[d]))
            labels.append(self.dates[d])
        handles.append(plt.Line2D(range(10), range(10), color='r', linewidth=2))
        labels.append('Baseline conditions ({}-{})'.format(self.baseline_period[0], self.baseline_period[1]))
        handles.append(plt.Line2D(range(10), range(10), color='k', linewidth=1))
        labels.append('Boxes represent quartiles;'.format(self.baseline_period[0], self.baseline_period[1]))
        handles.append(plt.Line2D(range(10), range(10), color='k', linewidth=1))
        labels.append('Whiskers represent 1.5x the interquartile range')
        handles.append(plt.scatter(1, 1, c='k', s=6, marker='D'))
        labels.append('Outliers')

        figlegend = plt.figure(figsize=(3, 2))
        figlegend.legend(handles, labels, title='Explanation', loc='center')

        outfile = os.path.join(self.output_base_folder, 'box_legend.pdf')
        figlegend.savefig(outfile, dpi=300)
        plt.close('all')


    def make_timeseries_legend(self):

        plt.close('all')
        plt.rcParams.update({'font.family': 'Univers 67 Condensed',
                             'font.size': 10})
        fig = plt.figure(1, (6, 2))

        grid = ImageGrid(fig, 111, # similar to subplot(111)
                            nrows_ncols = (1, 3), # creates 2x2 grid of axes
                            axes_pad=0.1) # pad between axes in inch

        scen = self.timeseries_properties.keys()
        for i in range(grid.ngrids):

            # background color for min/max
            grid[i].axvspan(xmin=0, xmax=1, facecolor=self.timeseries_properties[scen[i]]['color'],
                            alpha=self.timeseries_properties[scen[i]]['alpha'],
                            linewidth=0, zorder=0)

            # lines to represent means
            l = grid[i].axhline(y=0.5, xmin=0, xmax=1, color=self.timeseries_properties[scen[i]]['color'],
                                linewidth=4, zorder=1)
            l.set_path_effects([PathEffects.withStroke(linewidth=4, foreground="k")])

            # remove the ticks and size the plots
            grid[i].set_xticks([])
            grid[i].set_yticks([])
            grid[i].set_xlim(0, 0.5)

            # scenario labels
            grid[i].set_title(scen[i], loc='left', fontsize=10, family=self.title_font)

        # Labels for max/mean/min
        grid[i].text(1.2, 1, 'Maximum', ha='left', va='center',
                     transform=grid[i].transAxes, family=self.title_font)
        grid[i].text(1.2, .5, 'Mean from General Circulation Models', ha='left', va='center',
                     transform=grid[i].transAxes, family=self.title_font)
        grid[i].text(1.2, 0, 'Minimum', ha='left', va='center',
                     transform=grid[i].transAxes, family=self.title_font)

        grid[0].text(0, 1.7, "Explanation", ha='left', fontsize=14, family=self.title_font)
        grid[0].text(0, 1.33, "Emissions Scenarios", ha='left', family=self.title_font)
        plt.title('stuff')

        fig.subplots_adjust(top=0.5, left=-.25)

        outfile = os.path.join(self.output_base_folder, 'timeseries_legend.pdf')
        fig.savefig(outfile, dpi=300)
        plt.close()

#############
# Functions
##############


def thousands_sep(ax):
    # so clunky, but this appears to be the only way to do it
    if -10 > ax.get_ylim()[1] or ax.get_ylim()[1] > 10:
        fmt = '{:,.0f}'
    elif -10 < ax.get_ylim()[1] < -1 or 1 > ax.get_ylim()[1] > 10:
        fmt = '{:,.1f}'
    else:
        fmt = '{:,.2f}'

    def format_axis(y, pos):
        y = fmt.format(y)
        return y

    ax.get_yaxis().set_major_formatter(mpl.ticker.FuncFormatter(format_axis))


def ignore_outliers_in_yscale(dfs, factor=2):
    # rescales plot to next highest point if the highest point exceeds the next highest by specified factor
    largest = np.array([])
    for df in dfs.itervalues():
        top_two = np.sort(df.fillna(0).values.flatten())[-2:]
        largest = np.append(largest, top_two)
    largest = np.sort(largest)
    if largest[-1] > factor * largest[-2]:
        l = largest[-2]
        # take log of max value, then floor to get magnitude
        # divide max value by magnitude and then multiply mag. by ceiling
        newlimit = np.ceil(l/10**np.floor(np.log10(l)))*10**np.floor(np.log10(l))
    else:
        newlimit = None
    return newlimit





def make_title(ax, title, zorder=200):
    wrap = 60
    title = "\n".join(textwrap.wrap(title, wrap)) #wrap title
    '''
    ax.text(.025, 1.025, title,
            horizontalalignment='left',
            verticalalignment='bottom',
            transform=ax.transAxes, zorder=zorder)
    '''
    # with Univers 47 Condensed as the font.family, changing the weight to 'bold' doesn't work
    # manually specify a different family for the title
    ax.set_title(title.capitalize(), family='Univers 67 Condensed', fontsize=14, loc='left')


def timeseries(dfs, ylabel, props, Synthetic_timepers,
                    clip_outliers=True, xlabel='', title=None, default_font='Univers 57 Condensed'):

    # dfs = list of dataframes to plot (one dataframe per climate scenario)
    # window= width of moving avg window in timeunits
    # function= moving avg. fn to use (see Pandas doc)
    # title= plot title, ylabel= y-axis label
    # spinup= length of time (years) to trim off start of results when model is 'spinning up'

    # set/modify Seaborn defaults

    sb.set_style("ticks", {'font.family': default_font,
                           'xtick.direction': 'in',
                           'ytick.direction': 'in',
                           'xtick.'
                           'axes.grid': False,
                           'grid.color': 'w'})

    # initialize plot
    fig = plt.figure()
    ax = fig.add_subplot(111, zorder=100)

    # global settings
    alpha = 0.5
    synthetic_timeper_color = '1.0'
    synthetic_timeper_alpha = 1 - (alpha * 0.7)

    for dfname in dfs.iterkeys():

        alpha = props[dfname]['alpha']
        color = props[dfname]['color']
        zorder = props[dfname]['zorder']

        try:
            dfs[dfname].mean(axis=1).plot(color=color, label=dfname, linewidth=1, zorder=zorder+20, ax=ax)
        except TypeError:
            print "Problem plotting timeseries. Check that spinup value was not entered for plotting after spinup results already discarded during aggregation."

        ax.fill_between(dfs[dfname].index, dfs[dfname].max(axis=1), dfs[dfname].min(axis=1),
                        alpha=alpha, color=color, edgecolor='k', linewidth=0.25, zorder=zorder+10)

    # rescale plot to ignore extreme outliers
    newylimit = ignore_outliers_in_yscale(dfs)
    if newylimit:
        ax.set_ylim(ax.get_ylim()[0], newylimit)


    # shade periods for which synthetic data were generated
    if len(Synthetic_timepers) > 0:
        for per in Synthetic_timepers:
            tstart, tend = per
            p = plt.axvspan(tstart, tend, facecolor=synthetic_timeper_color, alpha=synthetic_timeper_alpha,
                            linewidth=0, zorder=99)

    # make title
    make_title(ax, title)


    thousands_sep(ax) # fix the scientific notation on the y axis
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)

    plt.tight_layout()

    return fig, ax


def sb_violin_annual(boxcolumns, baseline, compare_periods, ylabel, xlabel='', title='', color=['SteelBlue', 'Khaki'],
                     default_font='Univers 57 Condensed'):

    sb.set_style("whitegrid", {'font.family': default_font})

    dates = ['-'.join(map(str, per)) for per in compare_periods]

    fig = plt.figure()
    try:
        ax = sb.violinplot(boxcolumns, names=dates, color=color)

        # plot the population of streamflows within each violin
        for i in range(len(compare_periods)):
            plt.scatter([i+1]*len(boxcolumns[i]), boxcolumns[i].tolist(), c='k', s=12, marker='o')

        ax.axhline(y=baseline[0], xmin=0.05, xmax=0.95, color='r', linewidth=2)

        # make title
        make_title(ax, title)

        thousands_sep(ax)
        ax.set_ylabel(ylabel)
        ax.set_xlabel(xlabel)

        # set reasonable lower y limit for violins
        # (kernals can dip below zero even if data doesn't; inappropriate for strictly positive variables)
        minval = np.min([b.min() for b in boxcolumns])
        if minval < 0:
            ymin = np.min([b.min() for b in boxcolumns])
        else:
            ymin = ax.get_ylim()[0]
        ax.set_ylim(ymin, ax.get_ylim()[1])

    except:
        print sys.exc_info()
        ax = None

    plt.tight_layout()
    return fig, ax


def sb_box_annual(boxcolumns, baseline, compare_periods, ylabel, xlabel='', title='', color=['SteelBlue', 'Khaki'],
                  default_font='Univers 57 Condensed'):

    sb.set_style("whitegrid", {'font.family': default_font})

    dates = ['-'.join(map(str, per)) for per in compare_periods]

    fig = plt.figure()
    ax = sb.boxplot(boxcolumns, names=dates, color=color, fliersize=12)

    ax.axhline(y=baseline[0], xmin=0.05, xmax=0.95, color='r', linewidth=2)

    # make title
    make_title(ax, title)

    thousands_sep(ax)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    #ax.set_ylim(0, ax.get_ylim()[1])

    plt.tight_layout()
    return fig, ax


def sb_box_monthly(boxcolumns, baseline, compare_periods, ylabel, xlabel='', title='', color=['SteelBlue', 'Khaki'],
                   xtick_freq=1,
                   default_font='Univers 57 Condensed'):
    # different method than annual because the boxes are grouped by month, with one tick per month


    sb.set_style("whitegrid", {'font.family': default_font})

    dates = ['-'.join(map(str, per)) for per in compare_periods]

    # set box widths and positions so that they are grouped by month
    n_periods = len(dates)
    spacing = 0.1 # space between months
    boxwidth = (1 - 2 * spacing)/n_periods
    positions = []
    for m in range(12):
        for d in range(n_periods):
            position = 0.5 + m + spacing + (boxwidth * (d+0.5))
            positions.append(position)

    # make the box plot
    fig = plt.figure()
    ax = sb.boxplot(boxcolumns, positions=positions, widths=boxwidth, color=color)

    xmin, xmax = ax.get_xlim()
    l = xmax - xmin

    # transform the box positions to axes coordinates (one tuple per box)
    positions_t = []
    for i in range(len(positions)):
        positions_t.append((((positions[i] - 0.5*boxwidth - xmin)/l), (positions[i] + 0.5*boxwidth - xmin)/l))

    for i in range(len(baseline)):
        ax.axhline(baseline[i], xmin=positions_t[i][0], xmax=positions_t[i][1], color='r', linewidth=2)

    # clean up the axes
    thousands_sep(ax) # fix the scientific notation on the y axis

    # reset the ticks so that there is one per month (one per group)
    frequency = xtick_freq # 1 for every month, 2 for every other, etc.
    ticks = (np.arange(12) + 1)[frequency-1::frequency]
    ax.set_xticks(ticks)
    months = []
    for tick in ax.get_xticks():
        month = calendar.month_abbr[tick]
        months.append(month)

    ax.set_xticklabels(months)

    # make title
    make_title(ax, title)

    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)


    plt.tight_layout()
    return fig, ax