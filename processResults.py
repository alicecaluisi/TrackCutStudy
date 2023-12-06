#!/usr/bin/env python3

"""
Post processing script to handle the QA output from trackJetQa i.e. resolution at high pT.
"""

import ROOT
from ROOT import TFile, TLegend, TCanvas, TString, gPad, TH1, TColor, TLatex, gROOT, TH1F, TF1, TArrow, TH2F, TProfile, kAzure, kRainbow
from os import path
import os
import configparser
import argparse
import numpy
import json
import pandas
import warnings

ROOT.gStyle.SetPalette(kRainbow)

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

canvas_list = {}
#histo_list = {}


#########################
# Johanna: 
#   - add multBinning for projections of ThNSparses uncertainty in ranges (needed once multiplicites are calibrated)
#   - add comparison step for different trackCuts and different data set + prepare standard legends and ratio plots based on what Alice did

#########################


def clear_canvaslist():
    global canvas_list
    l = list(canvas_list.keys())
    for i in l:
        canvas_list[i].Clear()
        del canvas_list[i]
    canvas_list = {}

def canvas(n, x=800, y=800,
           gridx=False, gridy=False,
           tickx=True, ticky=True,
           logx=False, logy=False, logz=True,
           marginx=None):

    global canvas_list
    if canvas_list.setdefault(n, None) is not None:
        can = canvas_list[n]
    else:
        can = TCanvas(f"canvas_{n}", n, x, y)
        can.SetTickx(tickx)
        can.SetTicky(ticky)
        can.SetGridx(gridx)
        can.SetGridy(gridy)
        can.SetLogx(logx)
        can.SetLogy(logy)
        can.SetLogz(logz)
        if x == 800:
            can.SetLeftMargin(0.15)
            can.SetRightMargin(0.13)
        elif x > 1000:
            can.SetLeftMargin(0.12)
            can.SetRightMargin(0.08)
        if marginx is not None:
            can.SetLeftMargin(marginx[0])
            can.SetRightMargin(marginx[1])
        can.SetBottomMargin(0.15)
        can.SetTopMargin(0.1)
        canvas_list[n] = can
    return can

def ProjectThN(hist, NumberOfAxis, dirName):
    for axis in range(0,NumberOfAxis):
        if "Centrality" in (hist.GetAxis(axis).GetTitle()):
            continue
        for next_axis in range(0,NumberOfAxis):
            if "Centrality" in (hist.GetAxis(next_axis).GetTitle()):
                continue
            if hist.GetAxis(axis).GetTitle() == hist.GetAxis(next_axis).GetTitle():
                continue
            h = hist.Projection(axis,next_axis)
            h.SetTitle(h.GetXaxis().GetTitle()+"vs"+h.GetYaxis().GetTitle())
            h.SetStats(0)
            if dirName+" "+h.GetYaxis().GetTitle()+"vs"+h.GetXaxis().GetTitle() in canvas_list:
                continue
            can = canvas(dirName+" "+h.GetTitle())
            can.SetLogz()
            h.SetTitle(" ")
            h.Draw("COLZ")

# TH2 histograms X profile
def profileTH2X(histo, dirName):
    h_profileX = histo.ProfileX()
    h_profileX.SetTitle(histo.GetTitle() + " X Profile")
    h_profileX.GetYaxis().SetTitle("Mean value")
    h_profileX.SetLineColor(kAzure+7)
    h_profileX.SetLineWidth(3)
    canX = canvas(dirName+" "+h_profileX.GetTitle())
    h_profileX.Draw("E")

def drawPlots(f, InputDir="", Mode="", Save=""):
    #all available histos
    Kine = {"pt", "pt_TRD", "eta", "phi", "etaVSphi", "EtaPhiPt"}
    TrackPar = {"x", "y", "z", "alpha", "signed1Pt", "snp", "tgl", "flags", "dcaXY", "dcaZ", "length", 
                "Sigma1Pt", "Sigma1Pt_Layer1", "Sigma1Pt_Layer2", "Sigma1Pt_Layers12", "Sigma1Pt_Layer4",
                "Sigma1Pt_Layer5", "Sigma1Pt_Layer6", "Sigma1Pt_Layers45", "Sigma1Pt_Layers56", "Sigma1Pt_Layers46", "Sigma1Pt_Layers456"}
    ITS = {"itsNCls", "itsChi2NCl", "itsHits"}
    TPC = {"tpcNClsFindable", "tpcNClsFound", "tpcNClsShared", "tpcNClsCrossedRows", "tpcFractionSharedCls", "tpcCrossedRowsOverFindableCls", "tpcChi2NCl"}
    EventProp = {"collisionVtxZ", "collisionVtxZnoSel", "collisionVtxZSel8"}
    Mult = {"NTracksPV", "FT0M", "FT0A", "FT0C", "MultCorrelations"}
    TrackEventPar = {"Sigma1PtFT0Mcent", "Sigma1PtFT0Mmult", "Sigma1PtNTracksPV", "MultCorrelations"}
    Centrality = {"FT0M", "FT0A", "FT0C"}
    
    Directories = [Kine, TrackPar, ITS, TPC, EventProp, Mult, TrackEventPar, Centrality]

    # Current modes to run the script
    if Mode=="Tree":
        Directories = [Kine, TrackPar, ITS, TPC, EventProp]#Event Prop has to be the last  as we swith to the results file from the produce table
        
    if Mode=="Full":
        Centrality = {"FT0M", "FT0A", "FT0C"}
        Mult = {"FT0M", "MultCorrelations"}#only these are filled -> {"NTracksPV", "FT0M", "FT0A", "FT0C", "MultCorrelations"}
        TrackEventPar = {"MultCorrelations"}#only these are filled ->  {"Sigma1PtFT0Mcent", "Sigma1PtFT0Mmult", "Sigma1PtNTracksPV", "MultCorrelations"}
        Directories = [Kine, TrackPar, ITS, TPC, EventProp, Mult, TrackEventPar]

    if not f or not f.IsOpen():
        print("Did not get", f)
        return
    f.ls()
    for dir in Directories:
        dirName = " "
        if dir == Directories[0]:
            dirName = "Kine"
        elif dir == Directories[1]:
            dirName = "TrackPar"
        elif dir == Directories[2]:
            dirName = "ITS"
        elif dir == Directories[3]:
            dirName = "TPC"
        elif dir == Directories[4]:
            dirName = "EventProp"
            if Mode=="Tree":
                f.Close()
                f = TFile.Open(InputDir+"AnalysisResults.root", "READ")# the AnalysisResults.root file, produced on hyperloop with tree creation->Contains eventProp's.
        elif dir == Directories[5]:
            dirName = "Mult"
        elif dir == Directories[6]:
            dirName = "TrackEventPar"
        elif dir == Directories[7]:
            dirName = "Centrality"
            return
        for obj in dir:#case switch would be more elegant...
            o = f.Get(f"track-jet-qa/"+dirName+"/"+obj)
            if not o:
                print("Did not get", o, " as object ", obj)
            if "TH1" in o.ClassName():
                can = canvas(o.GetTitle())
                o.SetMarkerStyle(21)
                o.SetMarkerColor(4)
                o.GetYaxis().SetTitle("number of entries")
                if "pt" in o.GetName():
                    can.SetLogy()
                elif ("collisionVtxZ" in o.GetName()) or ("Mult"==dirName):
                    o.SetTitle("")# to still display number of events
                else:
                    o.SetTitle("")
                    o.SetStats(0)
                o.Draw("E")
            elif "TH2" in o.ClassName():
                can = canvas(o.GetTitle())
                can.SetLogz()
                o.SetStats(0)
                o.Draw("COLZ")
                profileTH2X(o, dirName)
            elif "TH3" in o.ClassName():
                #print(o.GetXaxis().GetTitle())
                histos = []
                for i in range(1,5):
                    N = o.GetNbinsX()
                    j = i*i
                    can = canvas(o.GetTitle()+str(i))
                    o.SetStats(0)
                    o.GetXaxis().SetRange(i, i*i)
                    h = o.Project3D("yz")
                    h.SetStats(0)
                    h.SetDirectory(0)
                    h.SetTitle("Projection range #it{p}_{T}: "+str(o.GetXaxis().GetBinCenter(i))+" - "+str(o.GetXaxis().GetBinCenter(j))+" GeV/#it{c}")
                    h.Draw("COLZ")
                    histos.append(h)
                    o.GetXaxis().SetRange(0, N)
            elif "THnSparse" in o.ClassName():
                ProjectThN(o,o.GetNdimensions(), dirName)
            else:
                print("we miss something..")
                print(o.ClassName())

        if Save=="True":
            dataSet = InputDir.strip("Results/"+"/AnalysisResults.root"+"/AnalysisResults_trees.root")
            print(dataSet)
            save_name = f"Save/{dataSet}/{dirName}.pdf"
            SaveCanvasList(canvas_list, dataSet, save_name)
            input("wait")
        else:
            print("Wait, we are at ")
            input(dirName)
            clear_canvaslist()

def SaveCanvasList(canvas_list, dataSet, save_name):
    n = 0
    for i in canvas_list:
        print(dataSet)
        save2 = f"Save/{dataSet}/"
        os.makedirs(os.path.dirname(save2), exist_ok=True)
        if n == 0:
            canvas_list[i].SaveAs(f"{save_name}[")
            #canvas_list[i].SaveAs(f"{save2}{dataSet}_{i}.png") #to save single images
        canvas_list[i].SaveAs(save_name.replace(".png", f"_{i}.png"))
        n += 1
        if n == len(canvas_list):
            canvas_list[i].SaveAs(f"{save_name}]")
    clear_canvaslist()

def compareDataSet(DataSets={}, Save=True):
    print("Compare full dataset results")

    
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--Mode", "-m", type=str,
                        default="Full", help="Specify if you want to run over the 'Full' or 'Tree' results")
    parser.add_argument("--Input", "-in", type=str,
                        default="Results/LHC22s_pass5/", help="Name of the directory where to find the AnalysisResults.root")
    parser.add_argument("--DataSets","-d", type=str,
                        default=["LHC23zzh_cpass1, LHC23zzh_cpass1"], help="Specify the results from the periods you want to compare")
    parser.add_argument("--Save", "-s", type=str,
                        default=["False", "True"], help="If you set this flag, it will save the documents")
    args = parser.parse_args()

    
    if args.Mode=="Tree":
        file = TFile.Open(args.Input+"AnalysisResults_trees.root", "READ")
        drawPlots(file, args.Input, args.Mode, args.Save)#to be a bit more extended + multBinning for sigma and pT projections

    if args.Mode=="Full":
        file = TFile.Open(args.Input, "READ")#+"AnalysisResults.root"
        drawPlots(file, args.Input, args.Mode, args.Save)

    if args.Mode=="ComparePeriod":
        compareDataSet(args.DataSets, args.Save)


    #compareCuts()

main()
    