#!/usr/bin/env python3
import ctt
from statistics import fmean
import matplotlib.pyplot as plt
import numpy as np
import datetime

def de_nodes():
    n = dict()
    for i in range(1,2489):
        n[f"dec{i:04}"] = []
    for i in range(1,83):
        n[f"deg{i:04}"] = []
    return n

def node_stats(node, cluster):
    issues = cluster.issue_list(target=node)
    status = []
    for i in issues:
        for c in i.comments:
            if c.comment == "opening issue" or c.comment == "reopening issue":
                status.append(('down',c.created_at))
            if c.comment == "closing issue":
                status.append(('up', c.created_at))
    status.sort(key=lambda x: x[1])
    return status

def update_avail(node, avail):
    date_len = len(node)
    for i in range(0, len(node), 2):
        if node[i][0] != 'down':
            print('something is wrong')
            print(i)
            print(node)
            x = 10/0
        start_down = (60*24*node[i][1].day)+(node[i][1].hour*60) + node[i][1].minute
        if node[i][1].month < 8:
            start_down = 0
        end_down = 60*24*31-1
        if i < date_len-1:
            if node[i+1][0] != 'up':
                print('thats not right')
                print(i)
                print(node)
                x = 5/0
            tmp = (60*24*node[i+1][1].day)+(node[i+1][1].hour*60) + node[i+1][1].minute
            if tmp < end_down:
                end_down = tmp
        for d in range(start_down, end_down+1):
            avail[d] -= 1

def plot(data):
    plt.style.use('_mpl-gallery')

    # make data
    x = np.linspace(0, 10, 100)
    y = 4 + 2 * np.sin(2 * x)
    x,y = zip(*timeseries)

    # plot
    fig, ax = plt.subplots()

    ax.plot(x, y, linewidth=2.0)
    plt.show()


def main():
    conf = ctt.get_config()
    cluster = ctt.CTT(conf)
    all_nodes = de_nodes()
    for n in all_nodes.keys():
        all_nodes[n] = node_stats(n, cluster)
    avail = [2570]*(60*24*31)
    for n in all_nodes:
        update_avail(all_nodes[n], avail)
    percent = [x/2570 for x in avail]
    print(sum(avail)/(2570*60*24*31))
    print(f"month avail: {fmean(percent)}")
    timeseries = [(datetime.datetime(2023,8,(x//(60*24))+1,hour=(x//60)%24, minute=x%60), percent[x]) for x in range((60*24*31))]



if __name__ == '__main__':
    main()
    import sys
    sys.exit(0)
